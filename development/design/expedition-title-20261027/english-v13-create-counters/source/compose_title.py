"""Fill only CREATE's R/A counters; preserve the reviewed v12 artwork and layout."""
from pathlib import Path
from collections import deque
from io import BytesIO
from PIL import Image
import numpy as np
import json, hashlib, base64

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
V12=BASE/'english-v12-tight-stack'
for folder in ['drafts','previews','evidence','source/layers','reference']:
    (ROOT/folder).mkdir(parents=True,exist_ok=True)
create=Image.open(V12/'source/layers/CREATE-front-only.png').convert('RGBA')
before=np.array(create);mask=np.zeros(before.shape[:2],bool)
components=[]
for letter,seed,expected in [('R',(529,167),3976),('A',(1229,167),4071)]:
    selected=np.zeros(mask.shape,bool);q=deque([seed])
    while q:
        x,y=q.popleft()
        if x<0 or y<0 or x>=create.width or y>=create.height or selected[y,x] or before[y,x,3]!=0:continue
        selected[y,x]=True
        q.extend([(x-1,y),(x+1,y),(x,y-1),(x,y+1)])
    ys,xs=np.where(selected)
    assert len(xs)==expected,(letter,len(xs))
    assert xs.min()>0 and ys.min()>0 and xs.max()<create.width-1 and ys.max()<create.height-1
    mask|=selected
    components.append({'letter':letter,'seed':seed,'pixels':len(xs),
                       'bbox_exclusive':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]})
after=before.copy();after[mask]=(0,0,0,255)
assert int(mask.sum())==8047
assert np.array_equal(before[~mask],after[~mask])
assert (after[mask]==np.array([0,0,0,255])).all()
create=Image.fromarray(after)
create.save(ROOT/'reference/CREATE-black-counters.png')
Image.fromarray(mask.astype('uint8')*255).save(ROOT/'reference/counter-fill-mask.png')

def svg_export(path,size,layers):
    w,h=size
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
           '<title>Minecraft / Create / Expedition</title>',
           '<metadata>Reviewed tight stack and wider Veridium highlights. CREATE foreground, R/A enclosed counters solid black. Three embedded raster layers.</metadata>']
    for label,im,xy in layers:
        buf=BytesIO();im.save(buf,format='PNG')
        uri='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        lines.append(f'<g id="{label}"><image x="{xy[0]}" y="{xy[1]}" width="{im.width}" height="{im.height}" href="{uri}"/></g>')
    lines.append('</svg>');path.write_text('\n'.join(lines))

previous=json.loads((V12/'evidence/composition.json').read_text())
records={}
for name,p in previous['placements'].items():
    size=tuple(p['canvas']);layers=[]
    for row in p['layers']:
        label=row['name'];im=create if label=='CREATE-front-only' else Image.open(V12/'source/layers'/(label+'.png')).convert('RGBA')
        assert im.size==tuple(row['size'])
        layers.append((label,im,tuple(row['xy'])))
    assert [x[0] for x in layers][-1]=='CREATE-front-only'
    canvas=Image.new('RGBA',size)
    for label,im,xy in layers:
        canvas.alpha_composite(im,xy);im.save(ROOT/'source/layers'/(label+'.png'))
    output=ROOT/'drafts'/('title-'+name+'.png');canvas.save(output)
    svg_export(ROOT/'source'/('title-'+name+'.svg'),size,layers)
    slate=Image.new('RGBA',size,(23,30,35,255));slate.alpha_composite(canvas)
    slate.convert('RGB').save(ROOT/'previews'/('title-'+name+'.jpg'),quality=97)
    for n in (1,2):
        bg=Image.open(BASE/f'reference/background-{n}.png').convert('RGBA');k=540/3124
        logo=canvas.resize((round(canvas.width*k),round(canvas.height*k)),Image.Resampling.LANCZOS)
        bg.alpha_composite(logo,((bg.width-logo.width)//2,6))
        bg.convert('RGB').save(ROOT/'previews'/(name+f'-menu-{n}.jpg'),quality=95)
    records[name]={'canvas':size,'layers':[{'name':label,'xy':xy,'size':im.size,
                     'rgba_sha256':hashlib.sha256(im.tobytes()).hexdigest()} for label,im,xy in layers],
                  'png_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}

evidence={'change':'Only the two enclosed R/A counters in CREATE are filled solid black',
          'fill_RGBA':[0,0,0,255],'filled_pixel_count':int(mask.sum()),'components':components,
          'other_CREATE_pixels_exactly_unchanged':True,'layout_and_other_rows_unchanged_from_v12':True,
          'small_raster_aperture_and_other_spaces_untouched':True,
          'source_version':'english-v12-tight-stack','placements':records,'live_client_changed_in_this_chat':False}
(ROOT/'evidence/composition.json').write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence,indent=2))
