#!/usr/bin/env python3
"""
Neon Runner — 3.2" RPi touchscreen endless runner  (320x180)
TOUCH ONLY: tap/swipe UPPER screen = jump  |  tap/swipe LOWER screen = duck
Char select: tap a character -> instantly returns to menu. No back button.
"""
import pygame, math, random, sys, os

# ── Layout constants (320x180 base) ───────────────────────────────────────
SCREEN_W    = 320
SCREEN_H    = 180
FPS         = 60
HUD_H       = 16
GAME_TOP    = 16
GROUND_Y    = 167
TOUCH_SPLIT = 90
LANE_Y      = [53, 91, 129]
LANE_T, LANE_M, LANE_B = 0, 1, 2

# ── Palette ────────────────────────────────────────────────────────────────
C_BG     = (  5,   2,  15)
C_CYAN   = (  0, 230, 212)
C_PINK   = (255,  30, 162)
C_YELLOW = (255, 222,   5)
C_GREEN  = ( 30, 248, 100)
C_PURPLE = (185,   0, 248)
C_ORANGE = (255, 135,   0)
C_WHITE  = (255, 255, 255)
C_RED    = (255,  42,  42)
C_GRID   = ( 13,   6,  35)
C_DARK   = (  3,   1,   9)
C_GOLD   = (255, 198,  48)

OBS_GROUND, OBS_CEIL, OBS_PILLAR, OBS_LASER, OBS_MISSILE = range(5)
ST_MENU, ST_CHAR, ST_PLAYING, ST_GAMEOVER                = range(4)

CHARS = [
    {"name":"DUCK",  "body":(255,215, 30),"accent":(255,140,  0),"trail":(255,238,100)},
    {"name":"FROG",  "body":( 45,240, 80),"accent":( 18,165, 40),"trail":(120,255,150)},
    {"name":"ROBOT", "body":(  0,200,255),"accent":(175,  0,255),"trail":( 80,220,255)},
    {"name":"CAT",   "body":(255,128,206),"accent":(205, 55,150),"trail":(255,168,224)},
]


# ── Drawing helpers ────────────────────────────────────────────────────────

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def safe_rect(surf, col, rect, w=0, r=0):
    try:    pygame.draw.rect(surf, col, rect, w, border_radius=r)
    except: pygame.draw.rect(surf, col, rect, w)

def glow_circle(surf, color, cx, cy, rad, layers=4):
    for i in range(layers, 0, -1):
        gr = rad + i*4
        gs = pygame.Surface((gr*2, gr*2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*color, int(55/i)), (gr, gr), gr)
        surf.blit(gs, (cx-gr, cy-gr), special_flags=pygame.BLEND_ADD)

def glow_rect(surf, color, rect, layers=3):
    for i in range(layers, 0, -1):
        ex = i*3
        rr = pygame.Rect(rect.x-ex, rect.y-ex, rect.w+ex*2, rect.h+ex*2)
        gs = pygame.Surface((max(1,rr.w), max(1,rr.h)), pygame.SRCALPHA)
        gs.fill((*color, int(65/i)))
        surf.blit(gs, rr.topleft, special_flags=pygame.BLEND_ADD)

def text_ctr(surf, font, txt, color, cx, y, shadow=None):
    if shadow:
        s = font.render(txt, True, shadow)
        surf.blit(s, (cx - s.get_width()//2 + 2, y+2))
    t = font.render(txt, True, color)
    surf.blit(t, (cx - t.get_width()//2, y))

def draw_btn(surf, rect, label, font, col, pressed=False):
    safe_rect(surf, (12, 6, 28), rect, 0, 8)
    safe_rect(surf, col, rect, 2, 8)
    if pressed:
        hi = pygame.Surface((rect.w-4, rect.h-4), pygame.SRCALPHA)
        hi.fill((*col, 75))
        surf.blit(hi, (rect.x+2, rect.y+2))
    sl = pygame.Rect(rect.x+3, rect.y+4, 4, rect.h-8)
    safe_rect(surf, col, sl, 0, 2)
    t = font.render(label, True, C_WHITE)
    surf.blit(t, (rect.x+12, rect.centery - t.get_height()//2))


# ── City background ───────────────────────────────────────────────────────

def make_city(W=640, H=64):
    s   = pygame.Surface((W, H), pygame.SRCALPHA)
    rng = random.Random(7)
    x   = 0
    while x < W:
        bw = rng.randint(12, 34); bh = rng.randint(10, H-4); by = H-bh
        s.fill((8, 4, 20, 248), (x, by, bw, bh))
        c = rng.choice([C_CYAN, C_PINK, C_PURPLE])
        pygame.draw.rect(s, (*c, 80), (x, by, bw, bh), 1)
        for wy in range(by+4, by+bh-2, 6):
            for wx in range(x+3, x+bw-2, 5):
                if rng.random() > 0.40:
                    wc = rng.choice([(255,222,95,150),(75,198,255,135),(255,88,198,125),(175,255,128,110)])
                    s.fill(wc, (wx, wy, 3, 3))
        if rng.random() > 0.52 and bw >= 16:
            ax = x + bw//2
            pygame.draw.line(s, (*C_CYAN, 70), (ax, by), (ax, by-6), 1)
            pygame.draw.circle(s, (*C_RED, 170), (ax, by-7), 2)
        x += bw + rng.randint(1, 4)
    return s


# ── Effect classes ─────────────────────────────────────────────────────────

class Ripple:
    def __init__(self, x, y):
        self.x=x; self.y=y; self.r=5; self.life=1.0
    def update(self): self.r+=4; self.life-=0.07
    def draw(self, surf):
        if self.life<=0 or self.r<2: return
        a=int(self.life*160); r=int(self.r)
        gs=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        pygame.draw.circle(gs,(0,230,210,a),(r+1,r+1),r,2)
        surf.blit(gs,(self.x-r-1,self.y-r-1))

class Popup:
    def __init__(self, x, y, text, color):
        self.x=float(x); self.y=float(y); self.text=text; self.color=color
        self.life=1.0; self.vy=-1.4
    def update(self): self.y+=self.vy; self.vy*=0.96; self.life-=0.020
    def draw(self, surf, font):
        if self.life<=0: return
        t=font.render(self.text, True, self.color)
        t.set_alpha(int(self.life*255))
        surf.blit(t,(int(self.x)-t.get_width()//2, int(self.y)))

class Particle:
    __slots__=('x','y','vx','vy','life','color','r','kind')
    TRAIL=0; SPARK=1; DOT=2
    def __init__(self, x, y, color, kind=2):
        self.x=float(x); self.y=float(y); self.kind=kind; self.color=color
        if kind==self.TRAIL:
            self.vx=random.uniform(-0.5, 0.2); self.vy=random.uniform(-0.7, 0.7)
            self.r=random.uniform(1.0, 2.5)
        elif kind==self.SPARK:
            angle=random.uniform(0, math.pi*2); spd=random.uniform(1.5, 5.0)
            self.vx=math.cos(angle)*spd; self.vy=math.sin(angle)*spd-1.0
            self.r=random.uniform(1.5, 3.5)
        else:
            self.vx=random.uniform(-2.5, 2.5); self.vy=random.uniform(-4.0,-0.5)
            self.r=random.uniform(1.5, 4.0)
        self.life=1.0
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=0.12
        self.life -= 0.040 if self.kind==self.TRAIL else 0.024
    def draw(self, surf):
        if self.life<=0: return
        a=int(self.life*215); r=max(1,int(self.r*self.life))
        ps=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        if self.kind==self.SPARK:
            ps.fill((*self.color, a),(1,1,r*2,r*2))
        else:
            pygame.draw.circle(ps,(*self.color,a),(r+1,r+1),r)
        surf.blit(ps,(int(self.x)-r-1,int(self.y)-r-1))


# ── Runner base ────────────────────────────────────────────────────────────

class Runner:
    def __init__(self, ci=0):
        self.char=CHARS[ci]; self.x=60
        self.lane=LANE_M; self.y=float(LANE_Y[LANE_M])
        self.target_y=float(LANE_Y[LANE_M]); self.vel_y=0.0
        self.t=0; self.alive=True; self.death_rot=0.0
    def jump(self):
        if self.lane>LANE_T:
            self.lane-=1; self.target_y=float(LANE_Y[self.lane]); self.vel_y=-8.0
    def duck(self):
        if self.lane<LANE_B:
            self.lane+=1; self.target_y=float(LANE_Y[self.lane]); self.vel_y=8.0
    def update(self):
        self.t+=1
        d=self.target_y-self.y; self.y+=d*0.22+self.vel_y*0.32; self.vel_y*=0.70
        if abs(d)<0.5: self.y=self.target_y; self.vel_y=0.0
        if not self.alive: self.death_rot=min(self.death_rot+5,180)
    def hit_rect(self): return pygame.Rect(int(self.x)-10,int(self.y)-9,20,18)
    def _squash(self):
        vy=abs(self.vel_y)
        if vy<0.5: return 1.0,1.0
        f=min(vy/8.0,1.0)*0.24; return 1.0-f, 1.0+f
    def _blit(self, surf, ds, x, y, angle):
        rot=pygame.transform.rotate(ds, angle)
        sx,sy=self._squash()
        if sx!=1.0:
            rw,rh=rot.get_size()
            rot=pygame.transform.scale(rot,(max(1,int(rw*sx)),max(1,int(rh*sy))))
        rw,rh=rot.get_size()
        surf.blit(rot,(x-rw//2, y-rh//2))
    def draw(self, surf): pass


# ── Duck ──────────────────────────────────────────────────────────────────

class DuckRunner(Runner):
    def draw(self, surf):
        x=int(self.x); y=int(self.y); C=self.char["body"]; A=self.char["accent"]; t=self.t
        ang=(math.sin(t*0.11)*8) if self.alive else -self.death_rot
        W=60; ds=pygame.Surface((W,W),pygame.SRCALPHA)
        cx=W//2-2; cy=W//2+4
        HL=tuple(min(255,v+85) for v in C)
        for gi in range(4,0,-1):
            pygame.draw.ellipse(ds,(*C,12*gi),(cx-18-gi*2,cy-10-gi*2,36+gi*4,22+gi*4))
        tb=int(math.sin(t*0.14)*3)
        pygame.draw.polygon(ds,A,[(cx-14,cy+4),(cx-27,cy-2+tb),(cx-23,cy+8+tb),(cx-12,cy+11)])
        pygame.draw.polygon(ds,HL,[(cx-15,cy+3),(cx-24,cy+tb),(cx-20,cy+9+tb)])
        pygame.draw.ellipse(ds,C,(cx-16,cy-10,32,22))
        pygame.draw.ellipse(ds,(255,248,160),(cx-7,cy-3,18,14))
        pygame.draw.ellipse(ds,(255,252,220),(cx-10,cy-8,18,9))
        pygame.draw.ellipse(ds,C,(cx+4,cy-19,12,15)); pygame.draw.circle(ds,C,(cx+11,cy-19),12)
        pygame.draw.circle(ds,HL,(cx+14,cy-22),6)
        bx=cx+22; by=cy-20
        pygame.draw.polygon(ds,A,[(bx,by-3),(bx+10,by-1),(bx+2,by+3)])
        pygame.draw.polygon(ds,(255,172,20),[(bx,by+1),(bx+9,by+2),(bx+2,by+5)])
        ex=cx+15; ey=cy-22
        pygame.draw.circle(ds,(18,8,38),(ex,ey),4); pygame.draw.circle(ds,(82,62,122),(ex,ey),3)
        pygame.draw.circle(ds,C_WHITE,(ex+1,ey-1),1)
        if (not self.alive) or (t%185<7):
            pygame.draw.line(ds,(18,8,38),(ex-4,ey),(ex+4,ey),2)
        flap=int(math.sin(t*0.20)*9)
        pygame.draw.polygon(ds,A,[(cx-3,cy+1),(cx-9,cy+5+flap//2),(cx-18,cy+8+flap),(cx-14,cy+13+flap*2//5),(cx-6,cy+11)])
        fb=int(math.sin(t*0.20)*3)
        for fx,fo in [(cx-12,0),(cx,fb)]:
            pygame.draw.ellipse(ds,A,(fx,cy+12+fo,12,4))
            for ti in range(3): pygame.draw.line(ds,A,(fx+2+ti*3,cy+12+fo),(fx+1+ti*4,cy+17+fo),1)
        self._blit(surf,ds,x,y,ang)


# ── Frog ──────────────────────────────────────────────────────────────────

class FrogRunner(Runner):
    def draw(self, surf):
        x=int(self.x); y=int(self.y); C=self.char["body"]; A=self.char["accent"]; t=self.t
        ang=(math.sin(t*0.09)*4) if self.alive else -self.death_rot
        W=58; ds=pygame.Surface((W,W),pygame.SRCALPHA)
        cx=W//2; cy=W//2+2
        HL=tuple(min(255,v+82) for v in C)
        for gi in range(4,0,-1):
            pygame.draw.ellipse(ds,(*C,12*gi),(cx-18-gi*2,cy-11-gi*2,36+gi*4,22+gi*4))
        pygame.draw.ellipse(ds,A,(cx-17,cy-10,34,20)); pygame.draw.ellipse(ds,C,(cx-16,cy-9,32,18))
        pygame.draw.ellipse(ds,(208,255,212),(cx-8,cy-4,18,12))
        pygame.draw.ellipse(ds,C,(cx+2,cy-24,22,16)); pygame.draw.ellipse(ds,(208,255,212),(cx+5,cy-19,14,9))
        for exi,eyo in [(-1,0),(11,1)]:
            ex=cx+4+exi; ey=cy-26+eyo
            pygame.draw.circle(ds,A,(ex,ey),8); pygame.draw.circle(ds,(22,36,22),(ex,ey),6)
            pygame.draw.circle(ds,C_GOLD,(ex,ey),3); pygame.draw.ellipse(ds,(6,14,6),(ex-2,ey-1,5,3))
            pygame.draw.circle(ds,C_WHITE,(ex+1,ey-1),1)
        tf=(t//8)%30
        if tf<5:
            ext=int(tf/5.0*11); tx2=cx+13+ext; ty2=cy-10+ext//4
            pygame.draw.line(ds,(218,48,78),(cx+13,cy-10),(tx2,ty2),2)
            pygame.draw.circle(ds,(252,78,98),(tx2,ty2),2)
        bob=int(math.sin(t*0.22)*4)
        for side in (-1,1):
            lx=cx+side*7; kx=lx+side*12; ky=cy+12
            pygame.draw.line(ds,A,(lx,cy+6),(kx,ky+bob*side),3)
            fx=kx+side*5
            pygame.draw.line(ds,C,(kx,ky+bob*side),(fx,cy+19),2)
            pygame.draw.ellipse(ds,A,(fx-4,cy+17,10,4))
        self._blit(surf,ds,x,y,ang)


# ── Robot ─────────────────────────────────────────────────────────────────

class RobotRunner(Runner):
    def draw(self, surf):
        x=int(self.x); y=int(self.y); C=self.char["body"]; A=self.char["accent"]; t=self.t
        ang=0 if self.alive else -self.death_rot
        W=56; H=60; ds=pygame.Surface((W,H),pygame.SRCALPHA)
        cx=W//2; cy=H//2+4
        HL=tuple(min(255,v+88) for v in C)
        fl=int(abs(math.sin(t*0.25))*8+4)
        for fi in range(fl,0,-1):
            fc=lerp_color(C_YELLOW,C_ORANGE,fi/max(1,fl))
            pygame.draw.ellipse(ds,(*fc,150),(cx-20,cy-fi+4,10,fi*2))
        for gi in range(4,0,-1):
            safe_rect(ds,(*C,10*gi),pygame.Rect(cx-16-gi*2,cy-12-gi*2,32+gi*4,24+gi*4),0,5)
        safe_rect(ds,A,pygame.Rect(cx-16,cy-12,32,24),0,5)
        safe_rect(ds,C,pygame.Rect(cx-15,cy-11,30,22),0,4)
        safe_rect(ds,HL,pygame.Rect(cx-11,cy-9,22,8),0,3)
        safe_rect(ds,(16,10,46),pygame.Rect(cx-8,cy-3,16,11),0,2)
        for bi,bh2 in enumerate([5,3,7,4,8,5]):
            pygame.draw.rect(ds,lerp_color(C_GREEN,C_CYAN,bi/5),(cx-6+bi*3,cy+5-bh2,2,bh2))
        safe_rect(ds,A,pygame.Rect(cx-11,cy-27,22,18),0,4)
        safe_rect(ds,C,pygame.Rect(cx-10,cy-26,20,16),0,3)
        safe_rect(ds,HL,pygame.Rect(cx-8,cy-24,16,7),0,2)
        safe_rect(ds,(10,5,30),pygame.Rect(cx-8,cy-21,16,6),0,2)
        scan=int(cx+math.sin(t*0.08)*6)
        ec=C_RED if not self.alive else C
        safe_rect(ds,ec,pygame.Rect(scan-4,cy-20,8,5),0,2)
        glow_rect(ds,ec,pygame.Rect(scan-4,cy-20,8,5),layers=2)
        pygame.draw.line(ds,A,(cx,cy-26),(cx-3,cy-34),2)
        bl=int(abs(math.sin(t*0.07))*255)
        pygame.draw.circle(ds,(bl,bl//2,0),(cx-3,cy-35),2)
        arm=int(math.sin(t*0.18)*4)
        safe_rect(ds,C,pygame.Rect(cx-21,cy-8+arm,8,10),0,2)
        safe_rect(ds,C,pygame.Rect(cx+13,cy-8-arm,8,10),0,2)
        pygame.draw.circle(ds,A,(cx-17,cy+3+arm),3); pygame.draw.circle(ds,A,(cx+17,cy+3-arm),3)
        step=int(math.sin(t*0.22)*5)
        for lx,lo in [(cx-10,step),(cx+2,-step)]:
            safe_rect(ds,A,pygame.Rect(lx,cy+11,8,13+lo),0,2)
            safe_rect(ds,C,pygame.Rect(lx+1,cy+12,6,11+lo),0,2)
            safe_rect(ds,A,pygame.Rect(lx-2,cy+22+lo,11,4),0,2)
        self._blit(surf,ds,x,y,ang)


# ── Cat ───────────────────────────────────────────────────────────────────

class CatRunner(Runner):
    def draw(self, surf):
        x=int(self.x); y=int(self.y); C=self.char["body"]; A=self.char["accent"]; t=self.t
        ang=(math.sin(t*0.11)*6) if self.alive else -self.death_rot
        W=62; ds=pygame.Surface((W,W),pygame.SRCALPHA)
        cx=W//2-2; cy=W//2+3
        HL=tuple(min(255,v+82) for v in C)
        for gi in range(4,0,-1):
            pygame.draw.ellipse(ds,(*C,12*gi),(cx-16-gi*2,cy-11-gi*2,32+gi*4,22+gi*4))
        tw=int(math.sin(t*0.14)*13); tw2=int(math.sin(t*0.14+0.8)*8)
        tpts=[(cx-12,cy+7),(cx-23,cy+3+tw//2),(cx-27,cy-4+tw),(cx-22,cy-10+tw2)]
        pygame.draw.lines(ds,A,False,tpts,4); pygame.draw.lines(ds,HL,False,tpts,2)
        pygame.draw.ellipse(ds,A,(cx-15,cy-10,30,20)); pygame.draw.ellipse(ds,C,(cx-14,cy-9,28,18))
        pygame.draw.ellipse(ds,HL,(cx-9,cy-7,18,10)); pygame.draw.ellipse(ds,(252,238,252),(cx-6,cy-4,14,12))
        pygame.draw.circle(ds,A,(cx+10,cy-17),13); pygame.draw.circle(ds,C,(cx+10,cy-17),12)
        pygame.draw.circle(ds,HL,(cx+12,cy-20),6)
        for ex4,idx in [(cx+1,0),(cx+16,2)]:
            pygame.draw.polygon(ds,C,[(ex4,cy-24),(ex4-3,cy-33),(ex4+7,cy-25)])
            pygame.draw.polygon(ds,A,[(ex4+idx,cy-25),(ex4+idx-1,cy-30),(ex4+idx+4,cy-26)])
        ex=cx+9; ey=cy-19
        pygame.draw.ellipse(ds,(24,14,46),(ex-3,ey-3,8,6)); pygame.draw.ellipse(ds,C_WHITE,(ex-2,ey-2,6,5))
        pygame.draw.ellipse(ds,(24,14,46),(ex,ey-2,3,5)); pygame.draw.circle(ds,C_WHITE,(ex+2,ey-1),1)
        pygame.draw.polygon(ds,A,[(cx+10,cy-13),(cx+8,cy-10),(cx+12,cy-10)])
        pygame.draw.arc(ds,C_ORANGE,(cx+2,cy-11,16,5),math.pi*0.18,math.pi*0.92,2)
        bs=int(math.sin(t*0.18)*2)
        pygame.draw.circle(ds,C_GOLD,(cx+10,cy-8+bs),3); pygame.draw.circle(ds,C_YELLOW,(cx+10,cy-8+bs),2)
        pb=int(math.sin(t*0.20)*3)
        for pwx,pwy in [(cx-11,cy+9),(cx+1,cy+9+pb)]:
            pygame.draw.ellipse(ds,A,(pwx,pwy,12,4))
            for ti in range(3): pygame.draw.circle(ds,HL,(pwx+2+ti*3,pwy+2),1)
        self._blit(surf,ds,x,y,ang)


RUNNER_CLASSES = [DuckRunner, FrogRunner, RobotRunner, CatRunner]


# ── Obstacle ───────────────────────────────────────────────────────────────

class Obstacle:
    def __init__(self, x, speed):
        self.x=float(x); self.base=speed; self.speed=speed; self.active=True; self.t=0
        self._gen()

    def _gen(self):
        self.kind=random.choices(
            [OBS_GROUND,OBS_CEIL,OBS_PILLAR,OBS_LASER,OBS_MISSILE],
            weights=[26,23,22,17,12])[0]
        if self.kind==OBS_GROUND:
            self.h=random.randint(26,46); self.w=random.randint(15,26)
            self.y=GROUND_Y-self.h; self.color=C_GREEN
            self.safe={LANE_T,LANE_M} if self.h<36 else {LANE_T}
        elif self.kind==OBS_CEIL:
            self.h=random.randint(26,46); self.w=random.randint(15,26)
            self.y=GAME_TOP; self.color=C_PINK
            self.safe={LANE_B,LANE_M} if self.h<36 else {LANE_B}
        elif self.kind==OBS_PILLAR:
            gl=random.choice([LANE_T,LANE_M,LANE_B]); gc=LANE_Y[gl]
            self.gap_t=gc-26; self.gap_b=gc+26; self.w=16; self.color=C_PURPLE
            self.safe={gl}
        elif self.kind==OBS_LASER:
            self.ll=random.choice([LANE_T,LANE_M,LANE_B]); self.ly=LANE_Y[self.ll]
            self.w=12; self.on=34; self.off=22; self.phase=0; self.beam=True
            self.color=C_RED; self.safe={l for l in [LANE_T,LANE_M,LANE_B] if l!=self.ll}
        elif self.kind==OBS_MISSILE:
            self.ml=random.choice([LANE_T,LANE_M,LANE_B]); self.my=float(LANE_Y[self.ml])
            self.w=28; self.h=10; self.color=C_ORANGE; self.speed=self.base*1.85
            self.safe={l for l in [LANE_T,LANE_M,LANE_B] if l!=self.ml}

    def update(self):
        self.t+=1; self.x-=self.speed
        if self.kind==OBS_LASER:
            self.phase+=1; p=self.on+self.off; self.beam=(self.phase%p)<self.on
        if self.x<-90: self.active=False

    def rects(self):
        ix=int(self.x)
        if self.kind==OBS_GROUND: return [pygame.Rect(ix,self.y,self.w,self.h)]
        if self.kind==OBS_CEIL:   return [pygame.Rect(ix,self.y,self.w,self.h)]
        if self.kind==OBS_PILLAR:
            r1=pygame.Rect(ix,GAME_TOP,self.w,max(0,self.gap_t-GAME_TOP))
            r2=pygame.Rect(ix,self.gap_b,self.w,max(0,GROUND_Y-self.gap_b))
            return [r for r in (r1,r2) if r.h>0]
        if self.kind==OBS_LASER:
            return [pygame.Rect(0,self.ly-4,max(1,ix),8)] if (self.beam and ix>0) else []
        if self.kind==OBS_MISSILE:
            return [pygame.Rect(ix,int(self.my)-5,self.w,self.h)]
        return []

    def draw(self, surf):
        ix=int(self.x)
        if self.kind in (OBS_GROUND,OBS_CEIL): self._spikes(surf,ix)
        elif self.kind==OBS_PILLAR:            self._pillar(surf,ix)
        elif self.kind==OBS_LASER:             self._laser(surf,ix)
        elif self.kind==OBS_MISSILE:           self._missile(surf,ix)

    def _spikes(self, surf, ix):
        k=self.kind; y=self.y; w=self.w; h=self.h; c=self.color
        pulse=0.60+0.40*math.sin(self.t*0.18)
        glow_rect(surf,tuple(int(v*pulse) for v in c),pygame.Rect(ix,y,w,h),layers=3)
        pygame.draw.rect(surf,c,(ix,y,w,h))
        hl=tuple(min(255,v+80) for v in c); pygame.draw.rect(surf,hl,(ix+2,y+2,w-4,3))
        n=max(2,w//10); sw=w//n
        for i in range(n):
            sx=ix+i*sw+sw//2; sh=9+int(math.sin(self.t*0.10+i)*2)
            if k==OBS_GROUND:
                pts=[(sx-sw//2+1,y),(sx,y-sh),(sx+sw//2-1,y)]
            else:
                base=y+h; pts=[(sx-sw//2+1,base),(sx,base+sh),(sx+sw//2-1,base)]
            pygame.draw.polygon(surf,c,pts)
            pygame.draw.line(surf,hl,pts[0],pts[1],1)

    def _pillar(self, surf, ix):
        c=self.color
        for r in self.rects():
            glow_rect(surf,c,r,layers=3)
            pygame.draw.rect(surf,(24,4,48),r); pygame.draw.rect(surf,c,r,2)
            hl=tuple(min(255,v+55) for v in c)
            for yy in range(r.y+5,r.y+r.h-4,8):
                w2=r.w-6
                pygame.draw.line(surf,hl,(r.x+3,yy),(r.x+3+w2//2,yy),1)
                pygame.draw.circle(surf,hl,(r.x+3+w2//2,yy),1)
                pygame.draw.line(surf,hl,(r.x+3+w2//2,yy),(r.x+r.w-3,yy-3),1)
        gcx=(self.gap_t+self.gap_b)//2; aw=3
        pygame.draw.polygon(surf,(*c,100),
            [(ix+self.w//2-aw,gcx-4),(ix+self.w//2+aw,gcx),(ix+self.w//2-aw,gcx+4)])

    def _laser(self, surf, ix):
        ly=self.ly; c=self.color; p=(self.on+self.off); ph=self.phase%p
        er=pygame.Rect(max(0,ix-10),ly-10,20,20)
        pygame.draw.rect(surf,(44,16,16),er); pygame.draw.rect(surf,c,er,2)
        if ph<self.on:
            if ix>2:
                pygame.draw.line(surf,C_WHITE,(0,ly),(ix,ly),2)
                pygame.draw.line(surf,c,(0,ly-2),(ix,ly-2),1)
                pygame.draw.line(surf,c,(0,ly+2),(ix,ly+2),1)
                for gi in range(5,0,-1):
                    a=int(35/gi); gs=pygame.Surface((max(1,ix),gi*3+2),pygame.SRCALPHA)
                    gs.fill((*c,a)); surf.blit(gs,(0,ly-gi),special_flags=pygame.BLEND_ADD)
            pygame.draw.circle(surf,C_WHITE,(ix,ly),4)
            glow_circle(surf,c,ix,ly,4,layers=3)
        else:
            frac=(ph-self.on)/self.off; alpha=int(72+62*math.sin(frac*math.pi*3))
            gs=pygame.Surface((SCREEN_W,4),pygame.SRCALPHA); gs.fill((*c,alpha))
            surf.blit(gs,(0,ly-2))
            pygame.draw.line(surf,C_WHITE,(ix,ly-6),(ix,ly+1),2)

    def _missile(self, surf, ix):
        y2=int(self.my); c=self.color
        for i in range(4):
            ex=ix+22+i*6; ey=y2+random.randint(-2,2); r=2+i; a=55-i*12
            if a>0 and 0<=ex<SCREEN_W:
                gs=pygame.Surface((r*2,r*2),pygame.SRCALPHA)
                pygame.draw.circle(gs,(170,170,170,a),(r,r),r); surf.blit(gs,(ex-r,ey-r))
        for _ in range(3):
            ex=ix+random.randint(18,30); ey=y2+random.randint(-3,3)
            if 0<=ex<SCREEN_W:
                pygame.draw.circle(surf,random.choice([C_YELLOW,C_ORANGE,C_RED]),(ex,ey),random.randint(1,3))
        body=pygame.Rect(ix,y2-5,26,10)
        glow_rect(surf,c,body,layers=3)
        pygame.draw.rect(surf,(50,25,4),body); pygame.draw.rect(surf,c,body,2)
        pygame.draw.rect(surf,C_WHITE,pygame.Rect(ix+3,y2-3,8,6))
        for i in range(3): pygame.draw.line(surf,C_DARK,(ix+11+i*4,y2-5),(ix+14+i*4,y2+5),2)
        pygame.draw.polygon(surf,C_YELLOW,[(ix+26,y2-5),(ix+36,y2),(ix+26,y2+5)])
        pygame.draw.polygon(surf,C_WHITE,  [(ix+26,y2-2),(ix+33,y2),(ix+26,y2+2)])
        hl=tuple(min(255,v+60) for v in c)
        pygame.draw.polygon(surf,c, [(ix+2,y2-5),(ix-7,y2-11),(ix+7,y2-5)])
        pygame.draw.polygon(surf,c, [(ix+2,y2+5),(ix-7,y2+11),(ix+7,y2+5)])
        pygame.draw.polygon(surf,hl,[(ix+2,y2-5),(ix-3,y2-8), (ix+6,y2-5)])
        pygame.draw.polygon(surf,hl,[(ix+2,y2+5),(ix-3,y2+8), (ix+6,y2+5)])


# ── Game ───────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Neon Runner")

        on_pi = not os.environ.get("DISPLAY") and sys.platform.startswith("linux")
        flags = (pygame.FULLSCREEN | pygame.NOFRAME) if on_pi else 0
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        self.clock  = pygame.time.Clock()

        # Fonts — slightly smaller to fit 180px height
        def mk(sz, bold=True):
            try:    return pygame.font.SysFont("monospace", sz, bold=bold)
            except: return pygame.font.Font(None, sz+4)
        self.f_xl  = mk(18)
        self.f_lg  = mk(13)
        self.f_md  = mk(11)
        self.f_sm  = mk(10, False)
        self.f_xs  = mk(9,  False)
        self.f_hint= pygame.font.Font(None, 11)

        self.city   = make_city()
        self.city_x = 0.0

        self.stars = [(random.randint(0,SCREEN_W),
                       random.randint(GAME_TOP,SCREEN_H),
                       random.uniform(0.4,2.1),
                       random.uniform(0,6.28)) for _ in range(45)]

        self.hi       = 0
        self.char_idx = 0

        # Touch state
        self._td   = None   # touch-down position
        self._tt   = 0      # touch-down time
        self._btn  = -1     # highlighted button index
        self._rips = []     # active Ripples

        # Visual state
        self._pops     = []
        self._shake    = 0
        self._flash    = 0
        self._dodge_cd = 0

        self._build_layout()
        self._init_game()
        self.state = ST_MENU  # must come after _init_game

    # ── layout ────────────────────────────────────────────────────────────

    def _build_layout(self):
        """All UI rects for 320x180."""
        cx = SCREEN_W // 2

        # Menu: 3 stacked buttons, y=82..168
        bw=200; bh=26; gap=4
        bx=(SCREEN_W-bw)//2
        self.menu_rects  = [pygame.Rect(bx, 82+i*(bh+gap), bw, bh) for i in range(3)]
        self.menu_labels = ["  START GAME", "  CHARACTERS", "  EXIT"]
        self.menu_colors = [C_GREEN, C_CYAN, C_PINK]

        # Char select: 4 buttons, y=26..143, NO back button
        cw=260; ch=27; cgap=3
        cx2=(SCREEN_W-cw)//2
        self.char_rects = [pygame.Rect(cx2, 26+i*(ch+cgap), cw, ch) for i in range(4)]

        # Game over buttons
        self.retry_rect  = pygame.Rect(cx-65, SCREEN_H-44, 130, 22)
        self.gomenu_rect = pygame.Rect(cx-50, SCREEN_H-19, 100, 18)

    # ── game init ─────────────────────────────────────────────────────────

    def _init_game(self):
        self.runner   = RUNNER_CLASSES[self.char_idx](self.char_idx)
        self.obs      = []
        self.parts    = []
        self._pops    = []
        self.score    = 0
        self._lscore  = 0
        self.speed    = 3.2
        self.dist     = 0.0
        self.stimer   = 0
        self.sgap     = 90
        self.bgx      = 0.0
        self.gndx     = 0.0
        self.city_x   = 0.0

    def _start_game(self):
        self._init_game()
        self.state = ST_PLAYING

    # ── touch ─────────────────────────────────────────────────────────────

    def _press(self, pos):
        self._td  = pos
        self._tt  = pygame.time.get_ticks()
        self._btn = -1
        self._rips.append(Ripple(*pos))
        if self.state == ST_MENU:
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(pos): self._btn = i
        elif self.state == ST_CHAR:
            for i, r in enumerate(self.char_rects):
                if r.collidepoint(pos): self._btn = i

    def _release(self, pos):
        # ── menu ──────────────────────────────────────────────────────────
        if self.state == ST_MENU:
            for i, r in enumerate(self.menu_rects):
                if r.collidepoint(pos):
                    if   i == 0: self._start_game()
                    elif i == 1: self.state = ST_CHAR
                    elif i == 2: pygame.quit(); sys.exit()
            self._btn = -1; self._td = None
            return

        # ── char select: tap = select + go straight to menu ───────────────
        if self.state == ST_CHAR:
            for i, r in enumerate(self.char_rects):
                if r.collidepoint(pos):
                    self.char_idx = i
                    self.runner   = RUNNER_CLASSES[i](i)  # update preview
                    self.state    = ST_MENU
                    self._btn = -1; self._td = None
                    return
            # Tapped empty space -> also return to menu
            self.state = ST_MENU
            self._btn = -1; self._td = None
            return

        # ── game over ─────────────────────────────────────────────────────
        if self.state == ST_GAMEOVER:
            if self.gomenu_rect.collidepoint(pos):
                self.state = ST_MENU
            else:
                self._start_game()
            self._td = None
            return

        # ── in-game ───────────────────────────────────────────────────────
        if self._td is None:
            self.runner.jump()
            return
        dx = pos[0]-self._td[0]; dy = pos[1]-self._td[1]
        d  = math.hypot(dx, dy)
        if d < 14:
            if pos[1] < TOUCH_SPLIT: self.runner.jump()
            else:                     self.runner.duck()
        elif abs(dy) >= abs(dx):
            if dy < -12: self.runner.jump()
            else:         self.runner.duck()
        else:
            self.runner.jump()
        self._td = None

    # ── collision ─────────────────────────────────────────────────────────

    def _collide(self):
        hr = self.runner.hit_rect().inflate(-3,-3)
        return any(hr.colliderect(r) for o in self.obs for r in o.rects())

    # ── update ────────────────────────────────────────────────────────────

    def update(self):
        for r in self._rips: r.update()
        self._rips = [r for r in self._rips if r.life > 0]
        if self.state != ST_PLAYING: return

        self._lscore = self.score
        self.runner.update()

        self.dist  += self.speed
        self.score  = int(self.dist / 55)
        self.speed  = min(3.2 + self.score*0.035, 10.0)

        for ms in (50, 100, 200, 350, 500, 750, 1000):
            if self._lscore < ms <= self.score:
                self._pops.append(Popup(SCREEN_W//2, 50, f"  {ms}  ", C_GOLD))
                self._flash = 12
        if self._flash > 0: self._flash -= 1

        if self._dodge_cd > 0: self._dodge_cd -= 1
        for o in self.obs:
            if self._dodge_cd == 0 and 55 < int(o.x) < 67:
                self._pops.append(Popup(self.runner.x, int(self.runner.y)-22, "DODGE", C_GREEN))
                self._dodge_cd = 30

        self.sgap   = max(40, 90 - self.score//2)
        self.stimer += 1
        if self.stimer >= self.sgap:
            self.obs.append(Obstacle(SCREEN_W+12, self.speed))
            self.stimer = 0

        for o in self.obs:
            if o.kind != OBS_MISSILE: o.speed = self.speed
            o.update()
        self.obs = [o for o in self.obs if o.active]

        for p in self.parts: p.update()
        self.parts = [p for p in self.parts if p.life > 0]
        if len(self.parts) < 120 and random.random() < 0.38:
            c = random.choice([C_CYAN, self.runner.char["trail"], C_WHITE])
            self.parts.append(Particle(
                self.runner.x - 14 + random.uniform(-3, 3),
                self.runner.y + random.uniform(-6, 6), c, Particle.TRAIL))

        for p in self._pops: p.update()
        self._pops = [p for p in self._pops if p.life > 0]

        self.bgx    = (self.bgx  + self.speed*0.38) % 40
        self.gndx   = (self.gndx + self.speed)      % 50
        self.city_x = (self.city_x + self.speed*0.16) % 640

        if self._collide():
            self.runner.alive = False
            self.state        = ST_GAMEOVER
            self.hi           = max(self.hi, self.score)
            self._shake       = 16
            for _ in range(40):
                self.parts.append(Particle(
                    self.runner.x + random.uniform(-14,14),
                    self.runner.y + random.uniform(-14,14),
                    random.choice([C_YELLOW,C_PINK,C_CYAN,C_WHITE,C_ORANGE]),
                    Particle.SPARK))

    # ── draw helpers ──────────────────────────────────────────────────────

    def _bg(self, surf, scroll=None):
        surf.fill(C_BG)
        ox = int(-(scroll if scroll is not None else pygame.time.get_ticks()*0.022)) % 40
        for gx in range(ox, SCREEN_W+40, 40):
            pygame.draw.line(surf, C_GRID, (gx,GAME_TOP), (gx,SCREEN_H))
        for gy in range(GAME_TOP, SCREEN_H+32, 32):
            pygame.draw.line(surf, C_GRID, (0,gy), (SCREEN_W,gy))
        t = pygame.time.get_ticks()*0.001
        for sx,sy,sz,ph in self.stars:
            bri = int((0.5+0.5*math.sin(t+ph))*sz*88); bri = max(14, min(bri,218))
            r   = max(1, int(sz*(0.5+0.5*math.sin(t+ph))))
            pygame.draw.circle(surf, (bri,bri,min(255,bri+26)), (sx,sy), r)
        for i in range(8):
            gy = GROUND_Y-10-i*4; v = max(0,9-i)*4
            pygame.draw.line(surf, (0,v,int(v*1.3)), (0,gy), (SCREEN_W,gy))
        # moon
        mx=250; my=34
        glow_circle(surf, C_PURPLE, mx, my, 10, layers=4)
        pygame.draw.circle(surf,(55,16,85), (mx,my),10)
        pygame.draw.circle(surf,(95,36,132),(mx,my),7)
        pygame.draw.circle(surf,(135,55,172),(mx+2,my-2),4)

    def _city(self, surf):
        H  = self.city.get_height(); y0 = GROUND_Y-H+2
        ox = int(-self.city_x) % 640
        surf.blit(self.city,(ox,y0)); surf.blit(self.city,(ox-640,y0))

    def _ground(self, surf):
        gy = GROUND_Y
        for i in range(5,0,-1):
            gs = pygame.Surface((SCREEN_W,3),pygame.SRCALPHA)
            gs.fill((0,238,218,26*i))
            surf.blit(gs,(0,gy-i*2),special_flags=pygame.BLEND_ADD)
        pygame.draw.line(surf,C_CYAN,(0,gy),(SCREEN_W,gy),2)
        dx = int(-self.gndx)
        while dx < SCREEN_W:
            pygame.draw.line(surf,(0,144,136),(dx,gy+4),(dx+14,gy+4),1); dx+=50

    def _lanes(self, surf):
        for ly in LANE_Y:
            x = 0
            while x < SCREEN_W:
                pygame.draw.line(surf,(20,12,48),(x,ly),(min(x+4,SCREEN_W),ly),1); x+=12
        for li,ly in enumerate(LANE_Y):
            col = (30,20,60) if li!=self.runner.lane else self.runner.char["body"]
            pygame.draw.circle(surf,col,(7,ly),3 if li==self.runner.lane else 2)
            if li==self.runner.lane: pygame.draw.circle(surf,C_WHITE,(7,ly),1)

    def _streaks(self, surf):
        if self.speed < 5.5: return
        f = min(1.0,(self.speed-5.5)/4.5)
        for _ in range(int(f*7)):
            sy = random.randint(GAME_TOP+3, GROUND_Y-3)
            ln = int(f*random.randint(12,50)); x2 = random.randint(3,75); a = int(f*115)
            gs = pygame.Surface((max(1,ln),1),pygame.SRCALPHA)
            gs.fill((*random.choice([C_CYAN,C_WHITE,(198,238,255)]),a))
            surf.blit(gs,(x2-ln,sy))

    def _hints(self, surf):
        if self.score > 8: return
        t  = pygame.time.get_ticks()*0.001; a = int(32+24*math.sin(t*1.5))
        up = pygame.Surface((18,10),pygame.SRCALPHA)
        pygame.draw.polygon(up,(0,228,210,a),[(9,0),(18,10),(0,10)]); surf.blit(up,(4,24))
        lu = self.f_hint.render("JUMP",True,C_CYAN); lu.set_alpha(a*3); surf.blit(lu,(4,36))
        dn = pygame.Surface((18,10),pygame.SRCALPHA)
        pygame.draw.polygon(dn,(255,28,160,a),[(0,0),(18,0),(9,10)]); surf.blit(dn,(4,TOUCH_SPLIT+8))
        ld = self.f_hint.render("DUCK",True,C_PINK); ld.set_alpha(a*3); surf.blit(ld,(4,TOUCH_SPLIT+20))

    def _hud(self, surf):
        pygame.draw.rect(surf,(2,1,8),(0,0,SCREEN_W,HUD_H))
        pygame.draw.line(surf,C_CYAN,(0,HUD_H),(SCREEN_W,HUD_H),1)
        sc = self.f_md.render(f"SCORE {self.score:05d}",True,C_CYAN); surf.blit(sc,(4,2))
        cn = self.f_xs.render(CHARS[self.char_idx]["name"],True,self.runner.char["body"])
        surf.blit(cn,(SCREEN_W//2-cn.get_width()//2,3))
        bw=40; bx=SCREEN_W-bw-4
        if self.hi > 0:
            hs = self.f_xs.render(f"HI {self.hi:05d}",True,(102,74,166))
            surf.blit(hs,(bx-hs.get_width()-4,3))
        frac=(self.speed-3.2)/6.8; pygame.draw.rect(surf,(16,8,42),(bx,3,bw,7))
        if frac>0:
            pygame.draw.rect(surf,lerp_color(C_GREEN,C_PINK,frac),(bx,3,max(1,int(frac*bw)),7))
        if self._flash > 0:
            fl = pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
            fl.fill((255,255,255,int(self._flash/12*70))); surf.blit(fl,(0,0))

    def _gameover_screen(self, surf):
        cx = SCREEN_W//2
        ov = pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA); ov.fill((0,0,0,145))
        surf.blit(ov,(0,0))
        pw=200; ph=114; px=cx-pw//2; py=22
        panel = pygame.Surface((pw,ph),pygame.SRCALPHA); panel.fill((10,4,34,220))
        safe_rect(panel,C_PINK,panel.get_rect(),2,12); surf.blit(panel,(px,py))
        text_ctr(surf,self.f_xl,"GAME OVER",C_PINK,cx,py+4,shadow=(68,0,44))
        sc2=self.f_lg.render(f"SCORE  {self.score:05d}",True,C_CYAN)
        surf.blit(sc2,(cx-sc2.get_width()//2, py+28))
        hs2=self.f_md.render(f"BEST   {self.hi:05d}",True,(148,104,226))
        surf.blit(hs2,(cx-hs2.get_width()//2, py+46))
        if self.score > 0 and self.score == self.hi:
            nb=self.f_sm.render("** NEW BEST! **",True,C_GOLD)
            surf.blit(nb,(cx-nb.get_width()//2, py+64))
        pulse=0.55+0.45*math.sin(pygame.time.get_ticks()*0.006)
        rt=self.f_md.render("TAP = RETRY",True,tuple(int(v*pulse) for v in C_YELLOW))
        surf.blit(rt,(cx-rt.get_width()//2, py+82))
        draw_btn(surf,self.gomenu_rect,"MENU",self.f_sm,C_CYAN)

    def _menu_screen(self):
        s  = self.screen; self._bg(s)
        t  = pygame.time.get_ticks()*0.001
        tc = tuple(int(v*(0.68+0.32*math.sin(t*2.1))) for v in C_YELLOW)
        text_ctr(s, self.f_xl, "NEON  RUNNER", tc, SCREEN_W//2, 5, shadow=(65,48,0))

        # Preview zone y=22..68
        prev_zone = pygame.Rect(SCREEN_W//2-36, 22, 72, 46)
        tmp = pygame.Surface((72,46), pygame.SRCALPHA)
        prev = RUNNER_CLASSES[self.char_idx](self.char_idx)
        prev.t = pygame.time.get_ticks()//16; prev.x=36; prev.y=28
        prev.draw(tmp)
        old_clip = s.get_clip(); s.set_clip(prev_zone)
        s.blit(tmp,(prev_zone.x,prev_zone.y)); s.set_clip(old_clip)

        # Hint + separator
        ui = self.f_hint.render("tap TOP=jump  tap BOTTOM=duck",True,C_CYAN)
        ui.set_alpha(130); s.blit(ui,(SCREEN_W//2-ui.get_width()//2,70))
        pygame.draw.line(s,C_GRID,(20,78),(SCREEN_W-20,78),1)

        for i,(r,lbl,col) in enumerate(zip(self.menu_rects,self.menu_labels,self.menu_colors)):
            draw_btn(s,r,lbl,self.f_md,col,self._btn==i)

        cr=self.f_xs.render("max_cyan",True,(44,28,78))
        s.blit(cr,(SCREEN_W-cr.get_width()-3,SCREEN_H-9))

    def _char_screen(self):
        """Tap a character -> select it and immediately return to menu."""
        s  = self.screen; self._bg(s)
        text_ctr(s,self.f_lg,"SELECT CHARACTER",C_CYAN,SCREEN_W//2,4,shadow=(0,44,44))
        text_ctr(s,self.f_xs,"Tap to select  •  tap outside to cancel",(80,65,110),SCREEN_W//2,16)

        for i,(r,ch) in enumerate(zip(self.char_rects,CHARS)):
            sel = (i == self.char_idx)
            col = ch["body"]
            fill = tuple(max(0,v//4) for v in col) if sel else (10,5,22)
            pygame.draw.rect(s,fill,r)
            pygame.draw.rect(s,col,r,3 if sel else 1)
            sw = pygame.Rect(r.x+2,r.y+2,7,r.h-4); pygame.draw.rect(s,col,sw)
            nt = self.f_md.render(ch["name"],True,C_WHITE)
            s.blit(nt,(r.x+14,r.centery-nt.get_height()//2))
            if sel:
                ind=self.f_xs.render("< ACTIVE",True,col)
                s.blit(ind,(r.right-ind.get_width()-5,r.centery-ind.get_height()//2))

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self):
        if self.state == ST_MENU:
            self._menu_screen()
        elif self.state == ST_CHAR:
            self._char_screen()
        else:
            shake = (0,0)
            if self._shake > 0:
                shake=(random.randint(-3,3),random.randint(-3,3)); self._shake-=1
            tgt = pygame.Surface((SCREEN_W,SCREEN_H))
            self._bg(tgt, self.bgx)
            self._city(tgt)
            self._ground(tgt)
            self._lanes(tgt)
            self._streaks(tgt)
            for p in self.parts: p.draw(tgt)
            for o in self.obs:   o.draw(tgt)
            self.runner.draw(tgt)
            self._hints(tgt)
            for pop in self._pops: pop.draw(tgt, self.f_md)
            self._hud(tgt)
            if self.state == ST_GAMEOVER: self._gameover_screen(tgt)
            for rip in self._rips: rip.draw(tgt)
            self.screen.fill(C_DARK); self.screen.blit(tgt,shake)
        pygame.display.flip()

    # ── main loop ─────────────────────────────────────────────────────────

    def run(self):
        while True:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif ev.type == pygame.KEYDOWN:
                    if   ev.key == pygame.K_UP:     self.runner.jump()
                    elif ev.key == pygame.K_DOWN:   self.runner.duck()
                    elif ev.key == pygame.K_ESCAPE:
                        if   self.state == ST_PLAYING:  self.state = ST_GAMEOVER
                        elif self.state in (ST_CHAR, ST_GAMEOVER): self.state = ST_MENU
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    self._press(ev.pos)
                elif ev.type == pygame.MOUSEBUTTONUP:
                    self._release(ev.pos)
                elif ev.type == pygame.FINGERDOWN:
                    self._press((int(ev.x*SCREEN_W), int(ev.y*SCREEN_H)))
                elif ev.type == pygame.FINGERUP:
                    self._release((int(ev.x*SCREEN_W), int(ev.y*SCREEN_H)))
            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()