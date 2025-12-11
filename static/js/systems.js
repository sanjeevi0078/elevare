(function(){
  const logEl = document.getElementById('wf-log');
  const statusEl = document.getElementById('wf-status');
  const startBtn = document.getElementById('wf-start');
  const stopBtn = document.getElementById('wf-stop');
  const ideaEl = document.getElementById('wf-idea');
  const mapNodes = Array.from(document.querySelectorAll('#wf-map .wf-node'));
  let es = null;

  function log(line, level='info'){
    const time = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `mb-1 ${level==='error'?'text-red-300':''}`;
    div.textContent = `[${time}] ${line}`;
    logEl.appendChild(div);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function setNodeActive(key){
    mapNodes.forEach(n => {
      if (n.dataset.key === key) n.classList.add('active');
      if (key === 'workflow_completed' && n.dataset.key === 'on_chain_end') n.classList.add('active');
    });
  }

  function start(){
    const idea = (ideaEl.value||'').trim();
    if (idea.length < 10) { log('Please enter a longer idea (>=10 chars)', 'error'); return; }
    if (es) { es.close(); }
    const conv = localStorage.getItem('elevare_user_id') || 'anon';
    const url = `${window.location.origin}/api/v1/agent/invoke/stream?` + new URLSearchParams({raw_idea: idea, conversation_id: conv, team_id: conv}).toString();
    es = new EventSource(url);
    statusEl.textContent = 'streaming';
    log('Streaming started…');

    es.addEventListener('workflow_started', ev => {
      setNodeActive('on_chain_start');
      log('Workflow started');
    });
    es.addEventListener('on_chain_start', ev => { setNodeActive('on_chain_start'); log('Chain started'); });
    es.addEventListener('on_tool_start', ev => { setNodeActive('on_tool_start'); log('Tool started'); });
    es.addEventListener('on_tool_end', ev => { log('Tool finished'); });
    es.addEventListener('on_chain_end', ev => { setNodeActive('on_chain_end'); log('Chain finished'); });
    es.addEventListener('workflow_completed', ev => {
      setNodeActive('on_chain_end');
      statusEl.textContent = 'completed';
      log('Workflow completed ✅');
      if (es) { es.close(); es = null; }
    });
    es.addEventListener('error', ev => {
      statusEl.textContent = 'error';
      log('Error: ' + (ev.data || 'unknown'), 'error');
    });
  }

  function stop(){ if (es) { es.close(); es = null; statusEl.textContent = 'stopped'; log('Stopped by user'); } }

  startBtn?.addEventListener('click', start);
  stopBtn?.addEventListener('click', stop);

  // Load status cards
  (async function loadStatus(){
    try{
      const h = await fetch(`${window.location.origin}/healthz`).then(r=>r.json());
      document.getElementById('sys-model').textContent = h.active_model || 'unknown';
    }catch{ document.getElementById('sys-model').textContent = 'error'; }
    try{
      const s = await fetch(`${window.location.origin}/mcp/status`).then(r=>r.json());
      document.getElementById('sys-mcp').textContent = s.reachable ? 'connected' : 'unavailable';
      const sub = s.reachable ? `${s.key_count} cached` : (s.error || '');
      document.getElementById('sys-mcp-sub').textContent = sub;
    }catch{ document.getElementById('sys-mcp').textContent = 'unavailable'; }
    try{
      const ideas = await fetch(`${window.location.origin}/ideas/`).then(r=>r.json());
      document.getElementById('sys-ideas').textContent = Array.isArray(ideas)?ideas.length:0;
    }catch{}
    try{
      const users = await fetch(`${window.location.origin}/matching/users`).then(r=>r.json());
      document.getElementById('sys-users').textContent = Array.isArray(users)?users.length:0;
    }catch{}
  })();
})();
