"""Run actual arena QA with read-only observations of renderer surface selection."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if '--layered' in sys.argv:
    sys.argv.remove('--layered')
    layered=(ROOT/'Tools/playtest_layered_maps.py').read_text()
    anchor="str(ROOT/'Tools/playtest_reference_arena.py')"
    assert layered.count(anchor)==1, "Layered arena subprocess anchor changed"
    layered=layered.replace(anchor, "str(ROOT/'Tools/capture_map_refinement.py')")
    exec(compile(layered,str(ROOT/'Tools/playtest_layered_maps.py'),'exec'))
    raise SystemExit(0)
source = (ROOT / 'Tools/playtest_reference_arena.py').read_text()
observation = r'''
const originalFloor=Renderer.prototype.drawFloorSlab;
const originalWall=Renderer.prototype.drawMasonry;
function observeSurface(renderer,x,y,kind) {
  const sample=renderer.surfaceSample(x,y), v=renderer.view;
  const observations=window.surfaceObservations ||= {explore:{},battle:{}};
  const phase=v.mode==='battle' ? 'battle' : 'explore';
  observations[phase][kind+':'+sample.x+','+sample.y]=sample;
}
Renderer.prototype.drawFloorSlab=function(sx,sy,tile,x,y,...rest) {
  observeSurface(this,x,y,'floor');
  return originalFloor.call(this,sx,sy,tile,x,y,...rest);
};
Renderer.prototype.drawMasonry=function(sx,sy,tile,x,y,...rest) {
  observeSurface(this,x,y,'wall');
  return originalWall.call(this,sx,sy,tile,x,y,...rest);
};
'''
needle='response=route.fetch(); source=response.text(); needle='
assert needle in source
source=source.replace(needle,'response=route.fetch(); source=response.text(); assert all(anchor in source for anchor in ("surfaceSample(x,y)","drawFloorSlab(","drawMasonry(")), "Surface diagnostic anchors changed"; source += '+repr(observation)+'; needle=')
needle="        assert (battle['width'],battle['height'])"
assert needle in source
check='''        observations=page.evaluate('window.surfaceObservations')
        compared=[]
        for kind in ('floor','wall'):
            for y in range(1,room['height']-1):
                for x in range(1,room['width']-1):
                    key=f"{kind}:{room['x']+x},{room['y']+y}"
                    if key not in observations['explore'] or key not in observations['battle']: continue
                    assert observations['explore'][key]==observations['battle'][key],('Surface identity changed',key)
                    compared.append({'cell':key,'sample':observations['battle'][key]})
        assert len(compared)>50,('Too few actual rendered surface cells',len(compared))
        (a.output/f'seed-{seed}-surface-consistency.json').write_text(json.dumps({'seed':seed,'actualKeyboardBattle':True,'disclosure':'Read-only renderer method observation; original drawing and game state unchanged. Only overlapping actual rendered interior room cells compared.','matchedCells':len(compared),'cells':compared},indent=2)+chr(10))
'''
source=source.replace(needle,check+needle)
exec(compile(source,str(ROOT/'Tools/playtest_reference_arena.py'),'exec'))
