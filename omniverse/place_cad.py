# -*- coding: utf-8 -*-
# 실 CAD(Layout.usd) 배치 테스트 — Z-up CAD를 Y-up 스테이지에 재배향/접지 후 카메라 프레이밍
import asyncio, carb, math
import omni.usd, omni.kit.app
from pxr import Usd, UsdGeom, UsdLux, Sdf, Gf

LAYOUT = r"C:\Users\user\AIWorkspace\siwha_usd\Layout.usd"

def world_bbox(stage, path):
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    rng = cache.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    return rng.GetMin(), rng.GetMax()

async def _go():
    app = omni.kit.app.get_app(); ctx = omni.usd.get_context()
    await ctx.new_stage_async()
    for _ in range(5): await app.next_update_async()
    st = ctx.get_stage()
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    st.SetDefaultPrim(UsdGeom.Xform.Define(st, "/World").GetPrim())

    # CAD 참조 + Z-up→Y-up (X축 -90°)
    plant = st.DefinePrim("/World/Plant", "Xform")
    plant.GetReferences().AddReference(LAYOUT)
    M = Gf.Matrix4d(1.0)
    M.SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), -90.0))
    UsdGeom.Xformable(plant).AddTransformOp().Set(M)
    for _ in range(10): await app.next_update_async()

    mn, mx = world_bbox(st, "/World/Plant")
    carb.log_warn("[PLACE] pre-ground bbox min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f)" % (mn[0],mn[1],mn[2],mx[0],mx[1],mx[2]))
    # 접지 + 중심(X,Z) 정렬
    cx = (mn[0]+mx[0])/2; cz = (mn[2]+mx[2])/2
    M2 = Gf.Matrix4d(1.0); M2.SetRotate(Gf.Rotation(Gf.Vec3d(1,0,0), -90.0))
    M2.SetTranslateOnly(Gf.Vec3d(-cx, -mn[1], -cz))
    UsdGeom.Xformable(plant).GetOrderedXformOps()[0].Set(M2)
    for _ in range(10): await app.next_update_async()
    mn, mx = world_bbox(st, "/World/Plant")
    carb.log_warn("[PLACE] grounded bbox min=(%.1f,%.1f,%.1f) max=(%.1f,%.1f,%.1f) size=(%.1f,%.1f,%.1f)" %
                  (mn[0],mn[1],mn[2],mx[0],mx[1],mx[2],mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2]))

    # 바닥 그리드 + 조명
    g = UsdGeom.Mesh.Define(st, "/World/Ground")
    S = 1500
    g.GetPointsAttr().Set([Gf.Vec3f(-S,0,-S),Gf.Vec3f(S,0,-S),Gf.Vec3f(S,0,S),Gf.Vec3f(-S,0,S)])
    g.GetFaceVertexCountsAttr().Set([4]); g.GetFaceVertexIndicesAttr().Set([0,1,2,3])
    g.GetSubdivisionSchemeAttr().Set(UsdGeom.Tokens.none)
    dome = UsdLux.DomeLight.Define(st, "/World/Sky"); dome.CreateIntensityAttr(1200.0)
    sun = UsdLux.DistantLight.Define(st, "/World/Sun"); sun.CreateIntensityAttr(3.0)
    UsdGeom.Xformable(sun.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-45,30,0))

    # 카메라 프레이밍(look-at)
    c = Gf.Vec3d((mn[0]+mx[0])/2, (mn[1]+mx[1])/2, (mn[2]+mx[2])/2)
    maxd = max(mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
    eye = c + Gf.Vec3d(0.8, 0.7, 0.9) * maxd * 1.1
    view = Gf.Matrix4d(); view.SetLookAt(eye, c, Gf.Vec3d(0,1,0))
    cam = UsdGeom.Camera.Define(st, "/World/DT_Cam")
    UsdGeom.Xformable(cam.GetPrim()).AddTransformOp().Set(view.GetInverse())
    cam.CreateFocalLengthAttr(22.0)
    cam.CreateClippingRangeAttr(Gf.Vec2f(1.0, 20000.0))
    for _ in range(20): await app.next_update_async()
    try:
        import omni.kit.viewport.utility as vpu
        vpu.get_active_viewport().camera_path = "/World/DT_Cam"
    except Exception as e:
        carb.log_warn("[PLACE] cam set skip %s" % e)
    carb.log_warn("[PLACE] DONE")

asyncio.ensure_future(_go())
carb.log_warn("[PLACE] scheduled")
