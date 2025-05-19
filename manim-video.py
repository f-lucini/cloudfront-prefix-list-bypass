from manim import *
from moviepy import VideoFileClip

class Cloudfront(Scene):
    def construct(self):
        self.camera.background_color = "#EEEEEE"
        cf_icon = ImageMobject("icons/CloudFront.png").scale(0.3).to_edge(UP*4)
        cf_text = Text('CloudFront', color='#8C4FFF', font='Verdana', font_size=18).next_to(cf_icon, DOWN)
        lb_icon = ImageMobject("icons/LoadBalancer.png").scale(0.3).to_edge(DOWN*3)
        lb_text = Text('Public ALB', color='#8C4FFF', font='Verdana', font_size=18).next_to(lb_icon, DOWN)
        arrow = always_redraw(lambda: Line(start=cf_text.get_bottom(), end=lb_icon.get_top(), buff=0.3, color='#747474').add_tip())
        waf_icon = ImageMobject("icons/WAF.png").scale(0.2).next_to(cf_icon, UP, buff=0.1)
        waf_text = Text('WAF', color='#DD344C', font='Verdana', font_size=18).next_to(waf_icon, UP)
        sg_text = Text('Security Group / Prefix List', color=RED, font='Verdana', font_size=18).next_to(lb_icon, UP, buff=0)
        sg_box = DashedVMobject(SurroundingRectangle(Group(sg_text, lb_icon, lb_text), color= RED, corner_radius=0.2), num_dashes=25)

        self.play(FadeIn(Group(cf_icon, cf_text)), Create(arrow), FadeIn(lb_icon, lb_text), run_time=0.75)
        self.wait(0.5)
        self.play(Wiggle(waf_icon), FadeIn(waf_text), GrowFromEdge(Group(sg_text, sg_box), UP), run_time=1)
        self.wait(0.5)

        group=Group(waf_text, waf_icon, cf_icon, cf_text, arrow, lb_icon, lb_text, sg_box, sg_text)
        group.generate_target()
        group.target.shift(3*RIGHT)
        cf2_icon = ImageMobject("icons/CloudFront.png").scale(0.3).to_edge(UP*4).to_edge(LEFT*2, buff=1.5)
        hat_icon = ImageMobject("icons/BlackHat.png").scale(0.2).next_to(cf2_icon, UP, buff=-0.5).set_z_index(1)
        cf2_text = Text('Attacker', color='#8C4FFF', font='Verdana', font_size=18).next_to(cf2_icon, DOWN)
        sg_box2 = DashedVMobject(SurroundingRectangle(Group(lb_icon, lb_text), color= RED, corner_radius=0.2), num_dashes=25)
        sg_box2.shift(3*RIGHT)
        lambda_icon = ImageMobject("icons/Lambda.png").scale(0.2).to_edge(LEFT*3, buff=1.5)
        lambda_text = Paragraph('Lambda\n@Edge', color='#ED7100', font='Verdana', font_size=18).next_to(lambda_icon, RIGHT, buff=0.2)
        host_text = Paragraph('Host\nHeader', color='#747474', font='Verdana', font_size=18, alignment="center", weight=BOLD).next_to(lambda_icon, DR)#, buff=1

        self.play(MoveToTarget(group), run_time=0.75)
        self.play(FadeOut(sg_text), Transform(sg_box, sg_box2), run_time=0.5)
        acc1_icon= SurroundingRectangle(Group(waf_text, waf_icon, cf_icon, cf_text, arrow, lb_icon, lb_text, sg_box), color="#2E73B8")
        acc1_text= Text('Your Account', color="#2E73B8", font='Verdana', font_size=18).next_to(acc1_icon, DOWN)
        self.play(FadeIn(Group(acc1_icon, acc1_text)), run_time=0.5)
        self.play(ApplyWave(hat_icon), FadeIn(Group(cf2_icon, cf2_text)), run_time=1)
        arrow2 = always_redraw(lambda: Line(start=cf2_text.get_bottom(), end=lb_icon.get_left(), path_arc=1.2, buff=0.5, color='#747474').add_tip())
        self.play(Create(arrow2), run_time=1)
        self.wait(0.5)
        self.play(FadeIn(Group(lambda_icon, lambda_text, host_text), shift=RIGHT))
        acc2_icon= SurroundingRectangle(Group(cf2_icon, hat_icon, cf2_text, lambda_icon, lambda_text, host_text), color="#CD2264")
        acc2_text= Text('Evil Account', color="#CD2264", font='Verdana', font_size=18).next_to(acc2_icon, UP)
        self.play(FadeIn(Group(acc2_icon, acc2_text)))

if __name__ == '__main__':
    scene = Cloudfront()
    scene.render()
    videoClip = VideoFileClip(scene.renderer.file_writer.movie_file_path)
    videoClip.write_gif("cf-bypass.gif",fps=25,loop=1)