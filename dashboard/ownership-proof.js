/* GRAIL ownership proof overlay — renders evidence strength after the main card renderer. */
(function(){
  function shortAddr(a){return a&&a.length>16?`${a.slice(0,7)}…${a.slice(-5)}`:a||''}
  function rowKey(card){
    const title=card.querySelector('h3')?.textContent||'';
    const mintText=card.querySelector('.mint')?.textContent||'';
    const m=mintText.match(/#(\d+)/);
    if(!m||typeof state==='undefined')return null;
    return state.rows.find(r=>String(r.collectible)===title&&Number(r.mint)===Number(m[1]))||null;
  }
  function paint(){
    if(typeof state==='undefined')return;
    document.querySelectorAll('.opportunity-card').forEach(card=>{
      const r=rowKey(card); if(!r)return;
      const proof=card.querySelector('.proof-chain');
      if(proof){
        if(r.owner_source_conflict){proof.textContent='OWNER CONFLICT';proof.dataset.kind='bad';proof.title='Provider-chain owner differs from exact-token owner; exact-token evidence is preferred.'}
        else if(r.owner_evidence_level==='exact-token'){proof.textContent='TOKEN ✓';proof.dataset.kind='good';proof.title=`Exact Collect token ${r.collect_token_id||''} verified on Collectscan.`}
        else if(r.owner_status==='verified-chain'){proof.textContent='CHAIN ✓';proof.dataset.kind='good';proof.title='Edition-level chain owner resolved by public provider lookup.'}
      }
      if(r.owner_source_conflict){
        const list=card.querySelector('.reasons');
        if(list&&!list.querySelector('.owner-conflict-note')){
          const li=document.createElement('li');li.className='owner-conflict-note';
          li.textContent=`Ownership source conflict: provider ${shortAddr(r.provider_owner)} vs exact token ${shortAddr(r.owner)}. Exact-token evidence is preferred.`;
          list.prepend(li);
        }
        const owner=card.querySelector('.owner-state');
        if(owner&&!card.classList.contains('is-owned')) owner.textContent=`Exact-token owner: ${shortAddr(r.owner)} · provider snapshot differs`;
      }
    });
  }
  const target=document.getElementById('cards');
  if(target)new MutationObserver(()=>queueMicrotask(paint)).observe(target,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',paint);
  setTimeout(paint,500);
})();
