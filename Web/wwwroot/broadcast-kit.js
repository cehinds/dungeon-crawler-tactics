const root='assets/broadcast-kit/';
const status=document.querySelector('#status');
function figure(src,label,detail=''){
 const f=document.createElement('figure'),a=document.createElement('a'),img=document.createElement('img'),caption=document.createElement('figcaption');
 a.href=root+src;a.download=src.split('/').pop();a.title='Download PNG: '+label;img.src=a.href;img.alt=label;img.loading='lazy';a.append(img);caption.textContent=label;
 if(detail){const small=document.createElement('small');small.textContent=detail;caption.append(small)}
 f.append(a,caption);return f;
}
try{
 const response=await fetch(root+'manifest.json');if(!response.ok)throw new Error('Manifest is not available yet.');
 const manifest=await response.json();
 for(const asset of manifest.assets){
  const edges=Object.entries(asset.edges??{}).map(([direction,tag])=>`${direction}: ${tag}`).join(' · ');
  const provenance=asset.derivation?'Derived structural variant':'Generated source component';
  document.querySelector('#pieces').append(figure(asset.src,asset.id,`${provenance} · ${asset.layer} · ${asset.adjacency}. ${edges}`));
 }
 status.textContent=`${manifest.assets.length} exported pieces: ${manifest.sourceComponentCount} source components and ${manifest.derivedStructuralCount} derived structural variants. ${manifest.status}`;
 for(const src of ['combat-concept.png','exploration-concept.png']){const f=figure(src,src.replace('.png','').replaceAll('-',' '));f.querySelector('img').addEventListener('error',()=>f.remove());document.querySelector('#concepts').append(f)}
}catch(error){status.textContent=error.message}
