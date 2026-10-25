"""Check actual floor PNG opacity and subpixel zoom/rotation joins in Chromium."""
import argparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://localhost:8127')
parser.add_argument('--browser', default='/usr/bin/chromium')
args = parser.parse_args()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
    page = browser.new_page()
    page.goto(args.url.rstrip('/') + '/book-tiles.html')
    result = page.evaluate('''async () => {
      const {floorLayer, drawFloorLayer} = await import('./tile-surface-renderer.js');
      const make = () => document.createElement('canvas');
      const source = make(); source.width = source.height = 256;
      const pen = source.getContext('2d'); pen.fillStyle = '#b7a27a'; pen.fillRect(64, 128, 128, 128);
      pen.fillStyle = '#45739d'; pen.fillRect(64, 128, 50, 30);
      const asset = {id:'fixture', anchor:{x:128,y:192}, derived:{offset:{x:64,y:128},width:128,height:128}};
      const images = new Map([['fixture', source]]);
      let joins = 0;
      for (let tileRotation = 0; tileRotation < 4; tileRotation++) {
        const pieces = Array.from({length:9}, (_,n) => ({asset, px:n%3*128, py:Math.floor(n/3)*128, angle:tileRotation*Math.PI/2}));
        const layer = floorLayer(pieces, images);
        if (layer !== floorLayer(pieces, images)) throw Error('Stable floor layer was not cached');
        const data = layer.canvas.getContext('2d').getImageData(0,0,384,384).data;
        for (let i=3; i<data.length; i+=4) if(data[i] !== 255) throw Error('Native floor layer has transparent join');
        const [cx,cy]=[[10,10],[118,10],[118,118],[10,118]][tileRotation], at=(cy*384+cx)*4;
        if(data[at]!==0x45||data[at+1]!==0x73||data[at+2]!==0x9d) throw Error('Floor rotation did not preserve the authored orientation');
        // Full-canvas PNG padding must never be sampled at individual shared edges.
        for (const zoom of [.27,.5,.73,1,1.25,1.83]) for(let rotation=0;rotation<4;rotation++) {
          const canvas=make();canvas.width=canvas.height=768;const ctx=canvas.getContext('2d');
          ctx.imageSmoothingEnabled=true;ctx.translate(384,384);ctx.rotate(rotation*Math.PI/2);ctx.scale(zoom,zoom);ctx.translate(-128,-128);
          drawFloorLayer(ctx,pieces,images);
          const inset=Math.floor(192*zoom)-2, pixels=ctx.getImageData(384-inset,384-inset,inset*2,inset*2).data;
          for(let i=3;i<pixels.length;i+=4) if(pixels[i] !== 255) throw Error(`Zoom seam at ${zoom}, rotation ${rotation}, tile ${tileRotation}`);
          joins++;
        }
      }
      const catalogURL=new URL('assets/book-tiles/catalog.json',location.href);
      const catalog=await fetch(catalogURL).then(r=>r.json());let floors=0;
      for(const kit of catalog.kits) for(const variant of Object.values(kit.variants)) {
        const url=new URL(variant.manifest,catalogURL), manifest=await fetch(url).then(r=>r.json());
        for(const asset of manifest.assets.filter(a=>a.squareLayout==='floor'&&a.cell<4)) {
          const image=new Image();image.src=new URL(asset.file,url);await image.decode();
          const canvas=make();canvas.width=canvas.height=128;const ctx=canvas.getContext('2d');const box=asset.derived;
          ctx.drawImage(image,box.offset.x,box.offset.y,128,128,0,0,128,128);
          const pixels=ctx.getImageData(0,0,128,128).data;
          for(let i=3;i<pixels.length;i+=4) if(pixels[i] !== 255) throw Error(`Transparent floor pixel: ${manifest.style}/${asset.id}`);
          floors++;
        }
      }
      return {joins, floors};
    }''')
    assert result['joins'] == 96
    assert result['floors'] > 0
    print(f"PASS {result['joins']} fractional zoom/rotation joins and {result['floors']} fully opaque exported floor planes.")
    browser.close()
