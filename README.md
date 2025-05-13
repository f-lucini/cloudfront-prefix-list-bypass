# CloudFront Prefix List Bypass

A cloud security research tool for demonstrating **CloudFront bypass**, designed to test AWS architectures that rely solely on **managed prefix list** for protection *without* properly implementing [origin cloaking](https://aws.amazon.com/developer/application-security-performance/articles/origin-cloaking).

## Overview

**Amazon CloudFront - AWS Content Delivery Network (CDN)** service - is the entry point to web applications, where *security controls* such as **Web Application Firewalls** are usually applied. Some organizations limit access to **public origins** (*e.g.: Application Load Balancers*) using [Amazon Managed Prefix Lists](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html#managed-prefix-list) with the assumption that restricting access to CloudFront IPs via *Security Groups* is a sufficient protection.

This tool highlights why this approach may be insufficient without additional security measures. **Since CloudFront IP addresses are shared across multiple accounts**, attackers could use their own *Distribution* with a custom DNS record to directly access the origin. By leveraging *Lambda@Edge* to inject the expected **Host header**—matching the target website's virtual host and TLS certificate—they can **bypass CDN-level security controls** (e.g., AWS WAF or geographic restrictions).

## Quick Start

The commands below will guide you through setting up the AWS attacker account with a **Lambda function** that modifies the *host-header*, along with the necessary IAM role and permissions in the **N. Virginia region** as required for [Lambda@Edge](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html).  Once configured, you can deploy a CloudFront Distribution for **each target origin** you need to access (using a different *stack name*).

`attacker-cf-distro.yml` accepts the following parameters as input values:
- **HostHeader**: *website DNS name* expected by the origin
- **OriginDomain**: *custom DNS record* pointing to the origin
- **Protocol** (*Optional*): protocol to use to connect to the origin
  - Default: [match-viewer](https://docs.aws.amazon.com/it_it/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-customoriginconfig.html#cfn-cloudfront-distribution-customoriginconfig-originprotocolpolicy)
  - Allowed values:
    - http-only
    - https-only
    - match-viewer

Install and configure **AWS CLI** on a Linux environment as prerequisite (launch the following commands with the proper *--profile* if needed) or manually upload the template using **AWS CloudFormation** Console.

1. Clone the repository

    ```bash
    git clone https://github.com/f-lucini/cloudfront-prefix-list-bypass.git
    cd cloudfront-prefix-list-bypass
    ```

2. Setup attacker environment (only for the first installation)
    ```bash
    aws cloudformation deploy --template-file attacker-lambda-setup.yml --stack-name sethost-lambda --region us-east-1
    ```

3. Deploy the attacker's distribution, assuming the **$target** variable contains the origin address (see the next paragraph for how to retrieve and reference it). Replace *example.domain* with the DNS name expected by the website.
    ```bash
    aws cloudformation deploy --template-file attacker-cf-distro.yml --stack-name cf-bypass --parameter-overrides HostHeader=example.domain OriginDomain=$target --region us-east-1

    # Get the distribution address
    aws cloudformation describe-stacks --stack-name cf-bypass --region us-east-1 --query 'Stacks[0].Outputs[0].OutputValue' --output json | sed 's/\"//g'
    ```

**Use the new distribution to access the origin** and bypass security settings on the original CDN: by default, the *Protocol* (HTTP or HTTPS) used to access the distribution is the same as that used to connect to the origin website. Additionally, due to CloudFront’s certificate validation process for TLS origins—which relies on the Host header—the *OriginDomain* **does not need to match the domain name on the certificate**. This could be useful to target HTTPS since, as explained below, **discovering an origin's IP address could be easier than determining its DNS name** (i.e., EC2 load balancers contain random strings).

## Technical Details

### Find Origin Address

The techniques used to uncover the origin server address, as described in this section, are based on the methods detailed in  [this article](https://infosecwriteups.com/finding-the-origin-ip-behind-cdns-37cd18d5275).

Tools like [CloakQuest3r](https://github.com/spyboy-productions/CloakQuest3r) or [SecurityTrails](https://securitytrails.com/), perform **subdomain scanning** to find misconfigured old records, or retrieve **DNS historical values** used before CDN deployment. Other services, such as [Censys](https://search.censys.io/), continually scan the entire public internet address space to **match IP using the same SSL certificate**: this data is used by the [CloudFlair](https://github.com/christophetd/CloudFlair) tool to **exclude Cloudfront IPs**, if the origin was scanned before the managed prefix list was applied. Similar techniques, like [Shodan favicon map](https://faviconmap.shodan.io), match websites with the same icon. For public Wordpress instances, the [pingback](https://www.invicti.com/blog/web-security/xml-rpc-protocol-ip-disclosure-attacks/) feature can be used to **log the origin**: however, using a private EC2 intance, would only expose the egress NAT IP.

### Reference Origin IP

Once found the origin IP address using one of the techniques above or additional architectural information leaks, a new CloudFront Distribution requires an **origin domain name** that must be *unique*. You can try **reversing lookup** the IP using `dig -x`, the standard [DNS string for EC2](https://www.reddit.com/r/aws/comments/6bple0/comment/dhokpps/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button) origins or alternatively register a record on a custom domain (tools like [no-ip](https://my.noip.com/dynamic-dns) allows one subdomain for free).

**Note:** Using an **HTTPS origin** you would expect a *certificate error* in the comunication between the attacker distribution and the origin since the certificate does not match the specified domain name. **However, Cloudfront will accept it, because the certificate includes [the correct host header](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html#using-https-cloudfront-to-origin-certificate)**. Futhermore, according to AWS documentation, Host header is *read-only* in CloudFront **viewer request**, but not in the [origin request](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/edge-function-restrictions-all.html#function-restrictions-read-only-headers).

This repository includes an **example of vulnerable ALB origin**, which you can *optionally* use to test the tool. The *ALB Listener* blocks all requests where the host header is not *example.domain* and only allows CloudFront prefix-list (for *N. Viriginia* region) via its security group rules.
```bash
# Deploy an example of vulnerable ALB origin
aws cloudformation deploy --template-file vulnerable-origin-example.yml --stack-name vulnerable-origin --region us-east-1

# Get the balancer DNS name
origin_dns=$(aws cloudformation describe-stacks --stack-name vulnerable-origin --region us-east-1 --query 'Stacks[0].Outputs[0].OutputValue' --output json | sed 's/\"//g')

# Simulate IP discovery using DNS resolution
origin_ip=$(echo $origin_dns | xargs -l dig +short | tail -1)

# Reverse the IP assuming us-east-1 region
target=$(echo ec2-$origin_ip | tr . - | xargs -I % -n 1 echo %.compute-1.amazonaws.com)
```

Deploy the attacker distribution as explained in the *Quick Start* to access the target using HTTP protocol; alternatively, you can test HTTPS behaviour by using the IP address of any public website.

### Prevention Guidelines
To protect against this type of bypass, follow best practices and implement origin cloaking effectively by:

- Using [VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) to ensure  resources are not accessible over the internet

- Restricting access to public origins like ALBs by validating a [custom header](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html)

## Cleanup

1. Delete Attacker CloudFormation distribution using the chosen **stack-name**.
    ```bash
    aws cloudformation delete-stack --stack-name cf-bypass
    ```

2. [*Optional*] Delete Lambda and IAM Role Infrastructure.
    ```bash
    aws cloudformation delete-stack --stack-name sethost-lambda
    ```
3. [*Optional*] If you deployed the test ALB, remember to destroy it.
    ```bash
    aws cloudformation delete-stack --stack-name vulnerable-origin
    ```