# -*- coding: utf-8 -*-
# 시화 조력발전소 — 실 CAD(Layout.usd) + 실제 환경(방조제·301호선 도로·바다/호소·시화나래 전망대)
# 좌표: Y-up, 미터. X=방조제 방향, Z=횡단(바다 -Z=서해 / 호소 +Z=시화호), Y=높이.
import asyncio, carb, math
import omni.usd, omni.kit.app
from pxr import Usd, UsdGeom, UsdShade, UsdLux, Sdf, Gf, Vt

LAYOUT = r"C:\Users\user\AIWorkspace\siwha_usd\Layout.usd"
_G = {}

# ---- 튜닝 상수 ----
# CAD가 플랜트 전체 포함: 수차10(−X반)+수문8(+X반)+윙월+호소측 도로(Y=35, z0~30)+크레인
GAP_HALF   = 238.0    # 방조제 시작 X — CAD ±236 수용
SEAWALL_END= 1900.0   # 방조제 X 끝(편측)
SEAWALL_ZW = 150.0    # 방조제 Z 폭
DECK_Y     = 35.0     # 상판 높이 = CAD 도로 레벨(Y≈35)
ROAD_Z     = 13.0     # 도로 중심 z (CAD 도로 밴드 0~30, 호소측)
WATER_Y    = 23.5     # 평균 수위(월드 Y) — 노출고 11.5m(실제 마루 EL+12.5·평균해면 EL0 비율), 만조 26.8
PROM_X     = -340.0   # 시화나래 곶 중심 X (발전동/−X 끝 옆) — 바다=−Z, 호소=+Z
# NVIDIA Omniverse 콘텐츠
CDN  = "https://omniverse-content-production.s3.us-west-2.amazonaws.com/Assets"
HDRI = CDN+"/Skies/Clear/white_cliff_top_4k.hdr"   # 바다 수평선 있는 맑은 하늘
TREES= ["Colorado_Spruce","Black_Oak","American_Beech","Chinese_Juniper","Douglas_Fir","Common_Apple","Dogwood"]

def s2l(c):
    c=c/255.0
    return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def hx(h): return Gf.Vec3f(s2l((h>>16)&255), s2l((h>>8)&255), s2l(h&255))

_n=[0]
class B:
    def __init__(self, st): self.st=st; self.mats={}
    def mat(self, name, col, r=0.7, m=0.0, e=None, op=1.0):
        if name in self.mats: return self.mats[name]
        p="/World/Looks/%s"%name
        mt=UsdShade.Material.Define(self.st,p); sh=UsdShade.Shader.Define(self.st,p+"/S")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor",Sdf.ValueTypeNames.Color3f).Set(hx(col))
        sh.CreateInput("roughness",Sdf.ValueTypeNames.Float).Set(r)
        sh.CreateInput("metallic",Sdf.ValueTypeNames.Float).Set(m)
        if e is not None: sh.CreateInput("emissiveColor",Sdf.ValueTypeNames.Color3f).Set(hx(e))
        if op<1.0: sh.CreateInput("opacity",Sdf.ValueTypeNames.Float).Set(op)
        mt.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(),"surface")
        self.mats[name]=mt; return mt
    def _p(self,tag,parent=None): _n[0]+=1; return "%s/%s_%d"%(parent or "/World/Env",tag,_n[0])
    def bind(self,prim,mt): UsdShade.MaterialBindingAPI.Apply(prim); UsdShade.MaterialBindingAPI(prim).Bind(mt)
    def box(self,size,pos,mt,rot=None,parent=None):
        c=UsdGeom.Cube.Define(self.st,self._p("box",parent)); c.GetSizeAttr().Set(1.0); pr=c.GetPrim()
        xf=UsdGeom.Xformable(pr); xf.ClearXformOpOrder(); xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
        xf.AddRotateXYZOp().Set(Gf.Vec3f(*(rot or (0,0,0)))); xf.AddScaleOp().Set(Gf.Vec3f(*size))
        self.bind(pr,mt); return pr,xf.GetOrderedXformOps()[0]
    def cyl(self,r,h,pos,mt,axis="Y"):
        c=UsdGeom.Cylinder.Define(self.st,self._p("cyl")); c.GetRadiusAttr().Set(r); c.GetHeightAttr().Set(h); c.GetAxisAttr().Set(axis)
        pr=c.GetPrim(); UsdGeom.Xformable(pr).AddTranslateOp().Set(Gf.Vec3d(*pos)); self.bind(pr,mt); return pr
    def cone(self,r,h,pos,mt,axis="Y"):
        c=UsdGeom.Cone.Define(self.st,self._p("cone")); c.GetRadiusAttr().Set(r); c.GetHeightAttr().Set(h); c.GetAxisAttr().Set(axis)
        pr=c.GetPrim(); UsdGeom.Xformable(pr).AddTranslateOp().Set(Gf.Vec3d(*pos)); self.bind(pr,mt); return pr
    def sphere(self,r,pos,mt,scale=None):
        s=UsdGeom.Sphere.Define(self.st,self._p("sph")); s.GetRadiusAttr().Set(r); pr=s.GetPrim()
        xf=UsdGeom.Xformable(pr); xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
        if scale is not None: xf.AddScaleOp().Set(Gf.Vec3f(*scale))
        self.bind(pr,mt); return pr
    def torus(self,R,r,pos,mt,segU=32,segV=14):
        path=self._p("torus"); mesh=UsdGeom.Mesh.Define(self.st,path)
        pts,counts,idx=[],[],[]
        for i in range(segU):
            a=2*math.pi*i/segU; ca,sa=math.cos(a),math.sin(a)
            for j in range(segV):
                bb=2*math.pi*j/segV; rr=R+r*math.cos(bb)
                pts.append(Gf.Vec3f(rr*ca,r*math.sin(bb),rr*sa))
        for i in range(segU):
            for j in range(segV):
                i2,j2=(i+1)%segU,(j+1)%segV
                aa=i*segV+j; bb2=i2*segV+j; cc=i2*segV+j2; dd=i*segV+j2
                counts.append(4); idx+=[aa,bb2,cc,dd]
        mesh.GetPointsAttr().Set(Vt.Vec3fArray(pts)); mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray(counts))
        mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(idx)); mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
        pr=mesh.GetPrim(); UsdGeom.Xformable(pr).AddTranslateOp().Set(Gf.Vec3d(*pos)); self.bind(pr,mt); return pr
    def ref(self,path,url,pos,rot=None,scale=None):
        p=self.st.DefinePrim(path,"Xform"); p.GetReferences().AddReference(url)
        xf=UsdGeom.Xformable(p); xf.ClearXformOpOrder()
        xf.AddTranslateOp().Set(Gf.Vec3d(*pos))
        if rot is not None: xf.AddRotateXYZOp().Set(Gf.Vec3f(*rot))
        if scale is not None:
            s=scale if isinstance(scale,(tuple,list)) else (scale,scale,scale)
            xf.AddScaleOp().Set(Gf.Vec3f(*s))
        return p
    def plane_grid(self,sx,sz,pos,mt,nx=64,nz=30):
        path=self._p("wgrid"); mesh=UsdGeom.Mesh.Define(self.st,path)
        base=[]; pts=[]
        for j in range(nz+1):
            for i in range(nx+1):
                x=-sx/2+sx*i/nx; z=-sz/2+sz*j/nz
                base.append((x,z)); pts.append(Gf.Vec3f(x,0,z))
        counts=[]; idx=[]
        for j in range(nz):
            for i in range(nx):
                a=j*(nx+1)+i; b2=a+1; cc=a+nx+2; dd=a+nx+1
                counts.append(4); idx+=[a,b2,cc,dd]
        mesh.GetPointsAttr().Set(Vt.Vec3fArray(pts))
        mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray(counts)); mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(idx))
        mesh.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
        pr=mesh.GetPrim(); xf=UsdGeom.Xformable(pr); op=xf.AddTranslateOp(); op.Set(Gf.Vec3d(*pos))
        self.bind(pr,mt)
        return op, mesh, base
    def plane(self,sx,sz,pos,mt):
        m=UsdGeom.Mesh.Define(self.st,self._p("plane")); hxx,hzz=sx/2,sz/2
        m.GetPointsAttr().Set([Gf.Vec3f(-hxx,0,-hzz),Gf.Vec3f(hxx,0,-hzz),Gf.Vec3f(hxx,0,hzz),Gf.Vec3f(-hxx,0,hzz)])
        m.GetFaceVertexCountsAttr().Set([4]); m.GetFaceVertexIndicesAttr().Set([0,1,2,3]); m.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
        pr=m.GetPrim(); xf=UsdGeom.Xformable(pr); xf.AddTranslateOp().Set(Gf.Vec3d(*pos)); self.bind(pr,mt)
        return pr, xf.GetOrderedXformOps()[0]

STATE_KR={"WAIT":"Head build-up","GEN":"GENERATING","WAIT_HIGH":"High-tide slack","SLUICE":"Draining (sluice)"}

class Sim:
    def __init__(s):
        s.amp=3.3; s.startHead=2.0; s.stopHead=0.8; s.nTurb=10; s.nGate=8; s.speed=180.0
        s.meanSea=5.0; s.periodHr=12.42; s.lakeArea=42e6
        s.t=0.0; s.sea=5.0; s.lake=2.0; s.state="WAIT"; s.totalMWh=0.0; s.cycE=0.0; s.lastCycle=0.0
        s.power=0.0; s.qIn=0.0; s.qOut=0.0
    def effH(s,H):
        t=max(0.0,min(1.0,(H-0.45)/1.45)); sm=t*t*(3-2*t); return 0.91*sm*(1-0.012*max(0.0,H-6.5))
    def turbFlow(s,H): return 0.0 if H<=0 else min(205*math.sqrt(H),600)
    def turbPow(s,H): return 0.0 if H<=0 else min(s.effH(H)*1000*9.81*s.turbFlow(H)*H/1e6,25.4)
    def gateFlow(s,rev): return 0.0 if rev<=0 else min(700*math.sqrt(rev),1400)
    def step(s,dtHr):
        s.t+=dtHr; ph=2*math.pi*s.t/s.periodHr; s.sea=s.meanSea+s.amp*math.sin(ph)
        rising=math.cos(ph)>0; head=s.sea-s.lake; rev=s.lake-s.sea; st=s.state
        if st=="WAIT":
            if rising and head>=s.startHead: st="GEN"
            elif (not rising) and rev>0.15: st="SLUICE"
        elif st=="GEN":
            if head<s.stopHead or ((not rising) and head<s.startHead*0.6): st="WAIT_HIGH"
        elif st=="WAIT_HIGH":
            if (not rising) and rev>0.1: st="SLUICE"
        elif st=="SLUICE":
            if rev<=0.05 or (rising and head>0):
                if s.cycE>0: s.lastCycle=s.cycE; s.cycE=0.0
                st="WAIT"
        s.state=st; dtSec=dtHr*3600.0; s.power=0.0; s.qIn=0.0; s.qOut=0.0
        if st=="GEN" and head>0:
            s.power=s.turbPow(head)*s.nTurb; s.qIn=s.turbFlow(head)*s.nTurb; s.cycE+=s.power*dtHr
        s.totalMWh+=s.power*dtHr
        if st=="SLUICE" and rev>0: s.qOut=s.gateFlow(rev)*s.nGate
        s.lake+=(s.qIn-s.qOut)*dtSec/s.lakeArea; s.lake=max(0.8,min(8.8,s.lake))
        return head,rev

class HUD:
    def __init__(s,sim):
        s.sim=sim; import omni.ui as ui; s.ui=ui
        F="C:/Windows/Fonts/malgun.ttf"
        def stl(sz,col=0xFFFFFFFF): return {"font":F,"font_size":sz,"color":col}
        s.win=ui.Window("Sihwa Tidal Power Plant - Digital Twin",width=400,height=310)
        with s.win.frame:
            with ui.VStack(spacing=5,style={"margin":8}):
                s.a=ui.Label("",height=28,style=stl(20,0xFF66E0FF)); s.b=ui.Label("",height=34,style=stl(28,0xFF7FE07A))
                s.c=ui.Label("",style=stl(16)); s.d=ui.Label("",style=stl(16)); s.e=ui.Label("",style=stl(16))
                s.f=ui.Label("",style=stl(16)); s.g=ui.Label("",style=stl(16,0xFF66D0FF)); s.h=ui.Label("",style=stl(16,0xFFFFD34D))
    def update(s,head,rev):
        m=s.sim
        s.a.text="* %s"%STATE_KR.get(m.state,m.state); s.b.text="Power   %.0f MW"%m.power
        s.c.text="Head H   %.2f m"%head; s.d.text="Turbine flow %.0f   Sluice %.0f  m3/s"%(m.qIn,m.qOut)
        s.e.text="Sea %.2f m    Lake %.2f m"%(m.sea,m.lake)
        non=m.nTurb if m.state=="GEN" else 0; s.f.text="Turbines %d/10    Gates %d/8"%(non,m.nGate)
        s.g.text=("Cumulative %.2f GWh"%(m.totalMWh/1000.0)) if m.totalMWh>=1000 else ("Cumulative %.0f MWh"%m.totalMWh)
        yr=m.lastCycle*1.932*365/1000.0; s.h.text="Last cycle %.0f MWh -> %.0f GWh/yr (target 552)"%(m.lastCycle,yr)

def world_bbox(st, path):
    cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_,UsdGeom.Tokens.render])
    rng=cache.ComputeWorldBound(st.GetPrimAtPath(path)).ComputeAlignedRange()
    return rng.GetMin(), rng.GetMax()

async def _go():
    app=omni.kit.app.get_app(); ctx=omni.usd.get_context()
    await ctx.new_stage_async()
    for _ in range(5): await app.next_update_async()
    st=ctx.get_stage()
    UsdGeom.SetStageUpAxis(st,UsdGeom.Tokens.y); UsdGeom.SetStageMetersPerUnit(st,1.0)
    st.SetDefaultPrim(UsdGeom.Xform.Define(st,"/World").GetPrim())
    UsdGeom.Xform.Define(st,"/World/Env")

    # --- CAD 참조(Z-up→Y-up, 접지, 중심) ---
    plant=st.DefinePrim("/World/Plant","Xform"); plant.GetReferences().AddReference(LAYOUT)
    # 명시적 축치환(행렬 행=각 로컬축의 목적지): Xc(171,횡단)->+Z, Yc(472,긴축)->+X, Zc(63,up)->+Y
    Rot=Gf.Matrix4d(0,0,1,0,  1,0,0,0,  0,1,0,0,  0,0,0,1)
    op=UsdGeom.Xformable(plant).AddTransformOp(); op.Set(Rot)
    for _ in range(10): await app.next_update_async()
    mn,mx=world_bbox(st,"/World/Plant")
    cx=(mn[0]+mx[0])/2; cz=(mn[2]+mx[2])/2
    M2=Gf.Matrix4d(Rot); M2.SetTranslateOnly(Gf.Vec3d(-cx,-mn[1],-cz))
    op.Set(M2)
    for _ in range(6): await app.next_update_async()
    mn,mx=world_bbox(st,"/World/Plant")
    carb.log_warn("[ENV] CAD grounded bbox X[%.0f,%.0f] Y[%.0f,%.0f] Z[%.0f,%.0f]"%(mn[0],mx[0],mn[1],mx[1],mn[2],mx[2]))

    b=B(st)
    mConc=b.mat("conc",0xc9c3b5,0.82,0.0); mDark=b.mat("dark",0x3a3f45,0.85,0.0)
    mAsph=b.mat("asph",0x24272b,0.88,0.0); mLine=b.mat("line",0xf2d34a,0.6,0.0)
    mSteel=b.mat("steel",0x5a6873,0.5,0.6); mWhite=b.mat("white",0xeef2f4,0.55,0.0)
    mGlass=b.mat("glass",0x2a5a78,0.15,0.4,op=0.5); mBeac=b.mat("beac",0xff3b30,0.4,0.0,e=0xff2018)
    mSea=b.mat("sea",0x1e4f66,0.02,0.05,op=0.93); mLake=b.mat("lake",0x1f6e63,0.03,0.05,op=0.85)
    mBed=b.mat("bed",0x5c5540,1.0,0.0); mYel=b.mat("yel",0xf2b134,0.6,0.0); mGate=b.mat("gate",0xc23b22,0.5,0.45)

    # --- 방조제(양측): 사다리꼴 제방(마루+사석 사면), 플랜트 윙월 구간(±215)까지 겹쳐 연결 ---
    mRip=b.mat("riprap",0x7d766a,1.0,0.0)
    EMB_X0=215.0
    for sgn in (-1,1):
        L=SEAWALL_END-EMB_X0; cxw=sgn*(EMB_X0+SEAWALL_END)/2
        b.box((L,4,44),(cxw,33,6),mConc)                     # 마루(도로면 z-16~+28)
        b.box((L,30,34),(cxw,16,6),mConc)                    # 코어
        b.box((L,6,48),(cxw,21.5,-35),mRip,rot=(-35,0,0))    # 바다측 사면
        b.box((L,6,48),(cxw,21.5, 47),mRip,rot=(35,0,0))     # 호소측 사면
    # --- 도로(지방도 301호선) : CAD 도로(Y35, z0~30)와 정렬·연속 관통 ---
    for sgn in (-1,1):
        L=SEAWALL_END-180.0; cxw=sgn*(180.0+SEAWALL_END)/2   # 안쪽 ±180까지 → CAD 도로(±183)와 접속
        b.box((L,0.8,19),(cxw,DECK_Y+0.4,ROAD_Z),mAsph)
        b.box((L,0.12,0.4),(cxw,DECK_Y+0.86,ROAD_Z),mLine)           # 중앙선
        for zz in (2.2,25.8):
            b.box((L,1.0,0.25),(cxw,DECK_Y+1.3,zz),mSteel)            # 난간(CAD 배리어 z2/26 정렬)
    # 플랜트-방조제 이음부: 윙월 뒤채움(사면이 윙월을 감싸도록)
    for sgn in (-1,1):
        b.box((34,26,70),(sgn*226.0,13,0),mConc)
    # --- 바다/호소 수면: 원거리 평면 + 근거리 파도 그리드(출렁임) ---
    seaZ=-1400.0; lakeZ=1400.0
    _,seaOp=b.plane(6400,2790,(0,WATER_Y-0.15,seaZ),mSea)
    _,lakeOp=b.plane(6400,2790,(0,WATER_Y-0.15,lakeZ),mLake)
    wSeaOp,wSeaMesh,wSeaBase=b.plane_grid(1600,760,(0,WATER_Y,-385),mSea,nx=72,nz=34)
    wLakeOp,wLakeMesh,wLakeBase=b.plane_grid(1600,760,(0,WATER_Y,385),mLake,nx=72,nz=34)
    # 해저
    b.box((7200,2,7200),(0,-4,0),mBed)

    # ================= 크레인: CAD 정적 크레인 숨기고 이동식 갠트리로 대체 =================
    cache2=UsdGeom.BBoxCache(Usd.TimeCode.Default(),[UsdGeom.Tokens.default_,UsdGeom.Tokens.render])
    hidden=0
    skip=("Turbine","Road","Foundation","Tank","Pip","Line","Actuator")
    lay=st.GetPrimAtPath("/World/Plant/Layout/Layout")
    if lay and lay.IsValid():
        for grp in lay.GetChildren():
            for ch in grp.GetChildren():
                nm=ch.GetName()
                if any(s in nm for s in skip): continue
                try:
                    rr=cache2.ComputeWorldBound(ch).ComputeAlignedRange()
                    c=(rr.GetMin()+rr.GetMax())*0.5; sz=rr.GetMax()-rr.GetMin()
                    if c[1]>39 and 6<sz[1]<45 and 6<sz[0]<75 and 18<sz[2]<95 and abs(c[0])<220:
                        UsdGeom.Imageable(ch).MakeInvisible(); hidden+=1
                        carb.log_warn("[ENV] hide crane cand: %s/%s c=(%.0f,%.0f,%.0f) sz=(%.0f,%.0f,%.0f)"%(grp.GetName(),nm,c[0],c[1],c[2],sz[0],sz[1],sz[2]))
                except Exception: pass
    carb.log_warn("[ENV] hidden cranes: %d"%hidden)
    # 크레인 경로 특정용 로깅(높이 40+, 중앙부, 긴 스팬)
    logged=0
    for p in st.Traverse():
        if not str(p.GetPath()).startswith("/World/Plant"): continue
        if not (p.IsA(UsdGeom.Mesh) or p.GetTypeName()=="Xform"): continue
        try:
            rr=cache2.ComputeWorldBound(p).ComputeAlignedRange()
            c=(rr.GetMin()+rr.GetMax())*0.5; sz=rr.GetMax()-rr.GetMin()
            if c[1]>30 and abs(c[0])<100 and sz[2]>25 and sz[0]<50 and sz[1]>3:
                carb.log_warn("[ENV] CRANE? %s c=(%.0f,%.0f,%.0f) sz=(%.0f,%.0f,%.0f)"%(str(p.GetPath()),c[0],c[1],c[2],sz[0],sz[1],sz[2]))
                logged+=1
                if logged>=20: break
        except Exception: pass
    # CAD 진짜 크레인(CR001) 이동 리깅 — prepend translate(CAD 로컬 Y=월드 X)
    craneMode=None
    crp=st.GetPrimAtPath("/World/Plant/Layout/Equipment/CR001")
    if crp and crp.IsValid():
        cxf=UsdGeom.Xformable(crp); olds=list(cxf.GetOrderedXformOps())
        craneOp=cxf.AddTranslateOp(opSuffix="move"); craneOp.Set(Gf.Vec3d(0,0,0))
        cxf.SetXformOpOrder([craneOp]+olds)
        craneMode='cad'; carb.log_warn("[ENV] CR001 rigged for motion")
    else:
        cr=UsdGeom.Xform.Define(st,"/World/Env/Gantry").GetPrim()
        crx=UsdGeom.Xformable(cr); crx.ClearXformOpOrder()
        craneOp=crx.AddTranslateOp(); craneOp.Set(Gf.Vec3d(-60,0,0))
        CB="/World/Env/Gantry"
        for zz in (-26.0,26.0):
            b.box((3.0,16,2.2),(0,DECK_Y+8,zz),mYel,parent=CB)
            b.box((5.0,1.2,4.0),(0,DECK_Y+0.6,zz),mYel,parent=CB)
        b.box((4.2,3.4,60),(0,DECK_Y+17.5,0),mYel,parent=CB)
        craneMode='env'; carb.log_warn("[ENV] fallback portal crane")
    _G['craneMode']=craneMode

    # 수문 게이트 리깅(이름에 gate 포함, +X 수문부 리프형) — SLUICE 시 인양
    _G['gates']=[]
    for p in st.Traverse():
        nm=p.GetName().lower()
        if 'gate' not in nm or not str(p.GetPath()).startswith("/World/Plant"): continue
        try:
            rr=cache2.ComputeWorldBound(p).ComputeAlignedRange()
            c=(rr.GetMin()+rr.GetMax())*0.5; szb=rr.GetMax()-rr.GetMin()
            if c[0]>5 and 3<szb[0]<26 and 4<szb[1]<20 and szb[2]<10 and len(_G['gates'])<8:
                xf2=UsdGeom.Xformable(p); olds2=list(xf2.GetOrderedXformOps())
                op2=xf2.AddTranslateOp(opSuffix="lift"); op2.Set(Gf.Vec3d(0,0,0))
                xf2.SetXformOpOrder([op2]+olds2); _G['gates'].append(op2)
                carb.log_warn("[ENV] gate rigged %s c=(%.0f,%.0f,%.0f)"%(p.GetName(),c[0],c[1],c[2]))
        except Exception: pass
    carb.log_warn("[ENV] gates rigged: %d"%len(_G['gates']))

    # 큰가리섬(서해측, 구글맵 위치)
    mIsl=b.mat("island",0x5f7a45,0.95,0.0)
    b.sphere(1.0,(-260,WATER_Y-3.0,-520),mIsl,scale=(95,12,75))
    for k,(ix,iz) in enumerate([(-285,-540),(-250,-505),(-230,-535),(-270,-490)]):
        b.ref("/World/Env/IslTree_%d"%k, CDN+"/Vegetation/Trees/%s.usd"%TREES[(k+3)%len(TREES)],
              (ix,WATER_Y+6.5,iz), rot=(0,(k*77)%360,0), scale=0.011)
    # ③ 양끝 물방울형 사석 섬(도류제) — 사용자 표시사진
    for (ix,iz,sx2,sz2) in [(-295,-72,52,20),(285,-50,48,18),(272,54,30,13)]:
        b.sphere(1.0,(ix,WATER_Y-2.0,iz),mRip,scale=(sx2,7,sz2))
        b.sphere(1.0,(ix,WATER_Y+3.0,iz),mIsl,scale=(sx2*0.62,2.6,sz2*0.6))

    # ================= 시화나래 전망대 + 방문자센터 + 곶 (발전동 -X 옆) =================
    px=PROM_X
    # ① 곶·전망대 = 바다측(−Z) — 사용자 표시사진·구글맵 마커 기준
    b.box((185,DECK_Y+1,120),(px+17,(DECK_Y+1)/2-1,-40),mConc)         # 곶 지반(플랜트 끝 −236까지 접속)
    b.box((150,DECK_Y+4,64),(px+10,(DECK_Y+4)/2,-52),mDark)
    mOrg=b.mat("org",0xd98a2b,0.6)
    b.box((40,10,26),(px-12,DECK_Y+5,-58),mWhite)                      # 방문자센터(문화관)
    b.box((26,7,18),(px+22,DECK_Y+3.5,-60),mOrg)                       # 오렌지동
    b.box((22,5,16),(px-2,DECK_Y+2.5,-80),mGlass)
    b.box((55,0.7,10),(px+62,DECK_Y-2.2,-26),mAsph,rot=(0,18,-8))      # 곶 진입 램프(위성 참조 간이)
    # 달전망대(75m) 상세: 테이퍼 샤프트 + UFO형 포드(유리띠·흰캡·녹색링) + 비콘 — 바다측 물가
    tbx,tbz=px+35,-52
    mPodG=b.mat("podglass",0x1d3a4d,0.12,0.4,op=0.62)
    mGrn2=b.mat("podgreen",0x69c04a,0.5,0.0,e=0x2f7a1e)
    b.cyl(11,7,(tbx,DECK_Y+3.5,tbz),mWhite,axis="Y")                   # 원형 로비(진입동)
    b.cyl(11.4,1.8,(tbx,DECK_Y+7.6,tbz),mGlass,axis="Y")               # 로비 유리띠
    b.cyl(4.6,22,(tbx,DECK_Y+11,tbz),mWhite,axis="Y")                  # 샤프트 하단
    b.cyl(4.0,22,(tbx,DECK_Y+33,tbz),mWhite,axis="Y")                  # 샤프트 중단(테이퍼)
    b.cyl(3.4,20,(tbx,DECK_Y+54,tbz),mWhite,axis="Y")                  # 샤프트 상단
    b.torus(4.35,0.12,(tbx,DECK_Y+22,tbz),mSteel)                      # 조인트 링
    b.torus(3.75,0.12,(tbx,DECK_Y+44,tbz),mSteel)
    b.sphere(1.0,(tbx,DECK_Y+67,tbz),mPodG,scale=(12,3.4,12))          # UFO 포드(유리)
    b.cyl(12.3,1.0,(tbx,DECK_Y+71,tbz),mWhite,axis="Y")                # 흰 지붕 캡
    b.torus(11.6,0.4,(tbx,DECK_Y+71.7,tbz),mGrn2)                      # 녹색 링(사진 특징)
    b.torus(10.9,0.15,(tbx,DECK_Y+72.3,tbz),mSteel)                    # 난간
    b.cyl(2.9,5,(tbx,DECK_Y+61.5,tbz),mWhite,axis="Y")                 # 포드 하부 칼라
    b.sphere(0.7,(tbx,DECK_Y+73.5,tbz),mBeac)                          # 항공비콘

    # ================= NVIDIA 에셋: 립랩(바위)·수목 =================
    rockxz=[]
    for i in range(22): rockxz.append((px-72+i*7.0,-102))
    for i in range(20): rockxz.append((-600+i*63.0, 42.0))    # 호소측 사면 수제선(Y26 기준)
    for i in range(20): rockxz.append((-600+i*63.0,-30.0))    # 바다측 사면 수제선(Y26 기준)
    # 에셋 cm 단위(mpu 0.01) → 100배 보정: 바위 ~0.1(2~3m 립랩), 나무 ~0.011(실제 크기)
    for k,(rx,rz) in enumerate(rockxz):
        b.ref("/World/Env/Rock_%d"%k, CDN+"/Vegetation/Rocks/rock_small_%02d.usda"%((k%15)+1),
              (rx,WATER_Y+0.3,rz), rot=(0,(k*47)%360,0), scale=(0.09+(k%4)*0.035,0.06,0.09+(k%3)*0.03))
    tzs=[(px-55,-90),(px-28,-80),(px-4,-96),(px+18,-86),(px+42,-98),(px-46,-110),(px+6,-112),(px+32,-74),(px-22,-68),(px+52,-80)]
    for k,(tx2,tz2) in enumerate(tzs):
        b.ref("/World/Env/Tree_%d"%k, CDN+"/Vegetation/Trees/%s.usd"%TREES[k%len(TREES)],
              (tx2,DECK_Y+0.5,tz2), rot=(0,(k*61)%360,0), scale=0.011)

    # ================= 조명: HDRI 하늘 + 태양 =================
    dome=UsdLux.DomeLight.Define(st,"/World/Sky")
    dome.CreateIntensityAttr(2200.0); dome.CreateTextureFileAttr().Set(HDRI); dome.CreateTextureFormatAttr().Set("latlong")
    sun=UsdLux.DistantLight.Define(st,"/World/Sun"); sun.CreateIntensityAttr(6.5); sun.CreateColorAttr(Gf.Vec3f(1.0,0.97,0.9)); sun.CreateAngleAttr(0.5)
    UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-52,195,0))  # 서해(−Z)면 조사

    carb.log_warn("[ENV] built prims=%d"%len(list(st.Traverse())))
    try:
        st.Export(r"C:\Users\user\AIWorkspace\siwha_usd\SihwaPlant_Env.usd"); carb.log_warn("[ENV] exported")
    except Exception as e: carb.log_warn("[ENV] export skip %s"%e)

    # --- 카메라 프레이밍(전체) ---
    for _ in range(10): await app.next_update_async()
    mn,mx=world_bbox(st,"/World/Plant")
    # 전면 = 서해(−Z)측에서 본 3/4 조감 — 전망대 곶(−340)까지 프레임에 포함
    c=Gf.Vec3d(-70, 18.0, 0)
    eye=Gf.Vec3d(-250, 240, -650)
    view=Gf.Matrix4d(); view.SetLookAt(eye,c,Gf.Vec3d(0,1,0))
    cam=UsdGeom.Camera.Define(st,"/World/DT_Cam")
    camOp=UsdGeom.Xformable(cam.GetPrim()).AddTransformOp(); camOp.Set(view.GetInverse())
    _G['camOp']=camOp
    cam.CreateFocalLengthAttr(20.0); cam.CreateClippingRangeAttr(Gf.Vec2f(1.0,40000.0))
    for _ in range(15): await app.next_update_async()
    try:
        import omni.kit.viewport.utility as vpu
        vpu.get_active_viewport().camera_path="/World/DT_Cam"
    except Exception as e: carb.log_warn("[ENV] cam skip %s"%e)

    # --- 조석 시뮬레이션(수위 애니메이션 + 한글 HUD) ---
    try:
        sim=Sim(); hud=HUD(sim)
        # 물살 파티클: 터빈 통수(노란빛, 바다→호소) / 수문 방류(백청, 호소→바다)
        import random
        tN=520; tPts=[[-228+216*random.random(), WATER_Y-1.2, -32+66*random.random()] for _ in range(tN)]
        tp=UsdGeom.Points.Define(st,"/World/Env/FlowTurb")
        tp.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*pp) for pp in tPts]))
        tp.GetWidthsAttr().Set(Vt.FloatArray([0.0]*tN))
        tp.CreateDisplayColorAttr(Vt.Vec3fArray([Gf.Vec3f(1.0,0.85,0.42)]))
        sN=420; sPts=[[18+210*random.random(), WATER_Y-1.0, 30-64*random.random()] for _ in range(sN)]
        sp2=UsdGeom.Points.Define(st,"/World/Env/FlowSluice")
        sp2.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*pp) for pp in sPts]))
        sp2.GetWidthsAttr().Set(Vt.FloatArray([0.0]*sN))
        sp2.CreateDisplayColorAttr(Vt.Vec3fArray([Gf.Vec3f(0.85,0.95,1.0)]))
        _G['fr']=0
        def _tick(e):
            try: dt=e.payload["dt"]
            except Exception: dt=1.0/60.0
            try:
                dtv=min(dt,0.05)
                head,rev=sim.step(dtv*sim.speed/3600.0)
                ySea=WATER_Y+(sim.sea-sim.meanSea); yLake=WATER_Y+(sim.lake-sim.meanSea)
                seaOp.Set(Gf.Vec3d(0,ySea-0.15,seaZ)); lakeOp.Set(Gf.Vec3d(0,yLake-0.15,lakeZ))
                wSeaOp.Set(Gf.Vec3d(0,ySea,-385)); wLakeOp.Set(Gf.Vec3d(0,yLake,385))
                _G['ct']=_G.get('ct',0.0)+dtv; t=_G['ct']; _G['fr']+=1
                # 출렁이는 파도(3프레임마다 정점 변위)
                if _G['fr']%3==0:
                    for mesh,base,amp,sp3 in ((wSeaMesh,wSeaBase,0.55,1.0),(wLakeMesh,wLakeBase,0.3,0.7)):
                        tt=t*sp3
                        arr=[Gf.Vec3f(x, amp*(0.6*math.sin(x*0.02+tt)+0.5*math.cos(z*0.03+tt*1.3)+0.25*math.sin((x+z)*0.09+tt*2.2)), z) for (x,z) in base]
                        mesh.GetPointsAttr().Set(Vt.Vec3fArray(arr))
                # ② 크레인: 발전동-수문 접합부 왕복(월드 −110~0)
                dxw=-55+55*math.sin(t*0.10)
                if _G.get('craneMode')=='cad': craneOp.Set(Gf.Vec3d(0, dxw+94.0, 0))
                else: craneOp.Set(Gf.Vec3d(dxw,0,0))
                # 수문 게이트 인양(SLUICE)
                tgt=1.0 if sim.state=="SLUICE" else 0.0
                _G['gp']=_G.get('gp',0.0)+(tgt-_G.get('gp',0.0))*0.05
                for gop in _G.get('gates',[]): gop.Set(Gf.Vec3d(0,0,9.0*_G['gp']))
                # 물살: GEN=터빈 통수(+Z), SLUICE=수문 방류(−Z)
                if sim.state=="GEN":
                    v=(10+head*4)*dtv
                    for p3 in tPts:
                        p3[2]+=v
                        if p3[2]>44: p3[2]=-34
                        p3[1]=(ySea if p3[2]<0 else yLake)+0.12+0.18*math.sin(t*3+p3[0]*0.1)
                    tp.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*pp) for pp in tPts]))
                    if _G.get('tw')!=1: tp.GetWidthsAttr().Set(Vt.FloatArray([1.1]*tN)); _G['tw']=1
                elif _G.get('tw')==1:
                    tp.GetWidthsAttr().Set(Vt.FloatArray([0.0]*tN)); _G['tw']=0
                if sim.state=="SLUICE":
                    v=(10+rev*4)*dtv
                    for p3 in sPts:
                        p3[2]-=v
                        if p3[2]<-46: p3[2]=32
                        p3[1]=(yLake if p3[2]>0 else ySea)+0.12+0.18*math.sin(t*3.4+p3[0]*0.1)
                    sp2.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*pp) for pp in sPts]))
                    if _G.get('sw')!=1: sp2.GetWidthsAttr().Set(Vt.FloatArray([1.2]*sN)); _G['sw']=1
                elif _G.get('sw')==1:
                    sp2.GetWidthsAttr().Set(Vt.FloatArray([0.0]*sN)); _G['sw']=0
                hud.update(head,rev)
            except Exception as ex: carb.log_error("[ENV] tick %s"%ex)
        _G['sim']=sim; _G['hud']=hud
        _G['sub']=app.get_update_event_stream().create_subscription_to_pop(_tick,name="siwha_env_tick")
        carb.log_warn("[ENV] SIM_RUNNING")
    except Exception as ex:
        import traceback; carb.log_error("[ENV] SIM_FAIL %s\n%s"%(ex,traceback.format_exc()))

    # ================= 영상 모드(SIWHA_VIDEO=gen|sluice): 상태 강제 + 근접캠 + 프레임 시퀀스 =================
    import os as _os
    vmode=_os.environ.get("SIWHA_VIDEO","")
    if vmode:
        try:
            sim.speed=600.0
            if vmode=="gen":       # 발전: 바다→호소 통수(밀물, 터빈 동작·물살이 호소로 유입)
                sim.t=2.0; sim.lake=3.2; sim.state="GEN"
                eye=Gf.Vec3d(-40,68,185); tgt=Gf.Vec3d(-120,6,15)       # 호소측 발전동 부감
            else:                  # 배수: 호소→바다 방류(수문 인양·물살이 바다로)
                sim.t=8.2; sim.lake=6.8; sim.state="SLUICE"
                eye=Gf.Vec3d(140,64,-185); tgt=Gf.Vec3d(195,4,-10)      # 바다측 수문 부감
            vv=Gf.Matrix4d(); vv.SetLookAt(eye,tgt,Gf.Vec3d(0,1,0)); _G['camOp'].Set(vv.GetInverse())
            import omni.kit.viewport.utility as vpu2
            vp2=vpu2.get_active_viewport()
            for _ in range(500): await app.next_update_async()          # 에셋 로딩+상태 안정
            seq=r"C:\Users\user\AIWorkspace\siwha_usd\frames_"+vmode
            _os.makedirs(seq,exist_ok=True)
            for i in range(450):
                vpu2.capture_viewport_to_file(vp2, seq+("\\f_%04d.png"%i))
                await app.next_update_async(); await app.next_update_async()
            for _ in range(150): await app.next_update_async()          # 파일 flush 대기
            carb.log_warn("[ENV] VIDEO_DONE %s"%vmode)
        except Exception as ex:
            import traceback; carb.log_error("[ENV] VIDEO_FAIL %s\n%s"%(ex,traceback.format_exc()))

    # --- 뷰포트 렌더 캡처: ① 서해 전면 ② 탑다운(배치 검증) ---
    try:
        import omni.kit.viewport.utility as vpu
        vp=vpu.get_active_viewport()
        if vmode: raise RuntimeError("video mode - skip stills")
        for _ in range(650): await app.next_update_async()   # 네트워크 에셋 로딩 대기
        vpu.capture_viewport_to_file(vp, r"C:\Users\user\AIWorkspace\siwha_usd\SihwaPlant_render.png")
        for _ in range(150): await app.next_update_async()
        v2=Gf.Matrix4d(); v2.SetLookAt(Gf.Vec3d(-60,1000,2),Gf.Vec3d(-60,20,0),Gf.Vec3d(0,0,-1))
        _G['camOp'].Set(v2.GetInverse())
        for _ in range(200): await app.next_update_async()
        vpu.capture_viewport_to_file(vp, r"C:\Users\user\AIWorkspace\siwha_usd\SihwaPlant_top.png")
        for _ in range(120): await app.next_update_async()
        carb.log_warn("[ENV] RENDER_CAPTURED")
    except Exception as ex:
        carb.log_warn("[ENV] capture skip %s"%ex)
    carb.log_warn("[ENV] DONE")

asyncio.ensure_future(_go())
carb.log_warn("[ENV] scheduled")
