(() => {
  const canvas = document.getElementById('rain');
  const ctx = canvas.getContext('2d');
  let W = canvas.width = innerWidth;
  let H = canvas.height = innerHeight;

  window.addEventListener('resize', () => {
    W = canvas.width = innerWidth;
    H = canvas.height = innerHeight;
    makeBokeh();
  });

  const rand = (a,b) => Math.random()*(b-a)+a;

  // multi-layer rain arrays
  const layers = [[],[],[]];
  function makeDrops(){
    layers[0].length = 0; // background slow fine mist
    layers[1].length = 0; // mid rain
    layers[2].length = 0; // foreground heavy drops
    const area = W*H;
    const bg = Math.max(40, Math.floor(area/15000));
    const mid = Math.max(80, Math.floor(area/8000));
    const fg = Math.max(50, Math.floor(area/12000));

    for(let i=0;i<bg;i++) layers[0].push(makeDrop(1.2, 0.9, 2.5, 10, 40));
    for(let i=0;i<mid;i++) layers[1].push(makeDrop(2.0, 1.6, 4.5, 14, 60));
    for(let i=0;i<fg;i++) layers[2].push(makeDrop(3.5, 2.2, 8.5, 18, 90));
  }

  function makeDrop(alphaMax, widthMin, speedMin, lenMin, lenMax){
    return {
      x: rand(0,W),
      y: rand(-H, H),
      len: rand(lenMin, lenMax),
      speed: rand(speedMin, speedMin*1.6),
      width: rand(0.6, widthMin),
      alpha: rand(0.08, alphaMax*0.12),
      wind: rand(-0.6,0.6)
    }
  }

  // floating dust particles
  const dust = [];
  function makeDust(){
    dust.length = 0;
    const count = Math.max(30, Math.floor((W*H)/200000));
    for(let i=0;i<count;i++) dust.push({x:rand(0,W), y:rand(0,H), r:rand(0.6,2.6), vx:rand(-0.1,0.1), vy:rand(-0.05,0.05), a:rand(0.02,0.12)});
  }

  // soft bokeh lights
  let bokehElems = [];
  function makeBokeh(){
    bokehElems = [];
    const count = 6;
    for(let i=0;i<count;i++){
      bokehElems.push({x:rand(W*0.05,W*0.95), y:rand(H*0.6,H*0.95), r:rand(30,120), a:rand(0.04,0.2), hue:rand(170,270)});
    }
  }

  function resetAll(){ makeDrops(); makeDust(); makeBokeh(); }

  function step(){
    // update drops
    for(const layer of layers){
      for(const d of layer){
        d.x += d.wind*0.6;
        d.y += d.speed;
        if(d.y > H + d.len){ d.y = -rand(10, H*0.2); d.x = rand(0,W); }
      }
    }
    // dust
    for(const p of dust){ p.x += p.vx; p.y += p.vy; if(p.x<0) p.x=W; if(p.x>W) p.x=0; if(p.y<0) p.y=H; if(p.y>H) p.y=0 }
  }

  function draw(){
    ctx.clearRect(0,0,W,H);

    // draw background subtle gradient (redundant with CSS but helps for screenshots)
    const g = ctx.createLinearGradient(0,0,0,H);
    g.addColorStop(0,'rgba(8,14,22,0.0)');
    g.addColorStop(1,'rgba(2,6,10,0.2)');
    ctx.fillStyle = g; ctx.fillRect(0,0,W,H);

    // soft bokeh lights
    for(const b of bokehElems){
      const rad = ctx.createRadialGradient(b.x,b.y,0,b.x,b.y,b.r);
      rad.addColorStop(0, `hsla(${b.hue},80%,70%,${b.a})`);
      rad.addColorStop(1, `hsla(${b.hue},70%,20%,0)`);
      ctx.globalCompositeOperation = 'screen';
      ctx.fillStyle = rad; ctx.fillRect(b.x-b.r, b.y-b.r, b.r*2, b.r*2);
    }

    // dust
    ctx.globalCompositeOperation = 'lighter';
    for(const p of dust){ ctx.fillStyle = `rgba(255,255,255,${p.a})`; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill(); }

    // rain layers back->front
    ctx.globalCompositeOperation = 'lighter';
    for(const d of layers[0]) drawDrop(d, 0.35);
    for(const d of layers[1]) drawDrop(d, 0.7);
    for(const d of layers[2]) drawDrop(d, 1.0);

    // slight window streaks / shiny overlay
    ctx.globalCompositeOperation = 'overlay';
    ctx.fillStyle = 'rgba(255,255,255,0.01)'; ctx.fillRect(0,0,W,H);

    requestAnimationFrame(loop);
  }

  function drawDrop(d, strength){
    ctx.beginPath();
    const a = Math.min(0.9, d.alpha * strength * 1.6);
    ctx.strokeStyle = `rgba(200,220,255,${a})`;
    ctx.lineWidth = d.width * (0.7 + strength*0.8);
    ctx.lineCap = 'round';
    ctx.moveTo(d.x, d.y);
    ctx.lineTo(d.x - d.wind*4, d.y - d.len);
    ctx.stroke();
  }

  function loop(){ step(); draw(); }

  // initial
  resetAll();
  loop();

  // no audio control included — audio was removed per request

})();
