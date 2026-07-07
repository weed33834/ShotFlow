(function () {
  'use strict';

  const i18n = {
    en: {
      title: "ShotFlow — Script in, 4K master out",
      meta_description: "A reproducible AIGC short-film pipeline. From script to 4K master, every parameter logged.",
      skip_to_content: "Skip to content",
      nav_pipeline: "Pipeline",
      nav_quickstart: "Quick Start",
      nav_platform: "Platform",
      nav_film: "The Film",
      nav_docs: "Docs",
      nav_github: "GitHub ↗",
      hero_badge: "AIGC Short-Film Pipeline",
      hero_title: "ShotFlow",
      hero_tagline: "Script in, 4K master out.",
      hero_desc: "A reproducible AIGC short-film pipeline. Twenty-four shots, twenty-nine keyframes, one 4K master — every parameter logged, every take reproducible.",
      hero_cta_primary: "View on GitHub",
      hero_cta_secondary: "GitCode Mirror",
      hero_cta_tertiary: "Quick Start ↓",
      stat_shots: "shots",
      stat_keyframes: "keyframes",
      stat_tests: "tests",
      stat_master: "master",
      scroll_hint: "Scroll to explore",
      prob_title: "What this solves",
      prob_sub: "The walls every AIGC short film hits, every single time.",
      prob1_title: "Character drift",
      prob1_desc: "The same character looks like a different person in every shot. Reference images drift, anchors slip, faces re-roll.",
      prob2_title: "Motion artifacts",
      prob2_desc: "Footage flickers, warps, and moves in ways nothing should move. Hands fuse, edges breathe, physics walks off the set.",
      prob3_title: "Prompt drift",
      prob3_desc: "The prompt and the storyboard drift apart, and the gap only shows up in the edit bay — when half the shots are already rendered.",
      prob4_title: "Lost parameters",
      prob4_desc: "Parameters vanish between sessions. The one good take can never be rerun, because nobody remembers what produced it.",
      prob5_title: "File chaos",
      prob5_desc: "Files get renamed, overwritten, lost. A small team burns more time hunting assets than making them.",
      resolve_title: "ShotFlow ties it together",
      resolve_desc: "One pipeline so a result is reproducible and a team can actually collaborate. Template, not product — swap in a story and go.",
      pipe_title: "The pipeline",
      pipe_sub: "Six stages, one parameter chain, one master.",
      stage1_title: "Script & World",
      stage1_desc: "DeepSeek / Claude. Script, worldbuilding, character bible.",
      stage2_title: "Keyframes",
      stage2_desc: "Flux.1 Kontext + IPAdapter. 29 reference frames, character stays on-model.",
      stage3_title: "Standard Shots",
      stage3_desc: "Wan2.2 I2V 14B. 19 image-to-video clips for dialogue and close-ups.",
      stage4_title: "Complex Shots",
      stage4_desc: "Kling 2.5 Turbo. 5 keyframe-to-keyframe shots for movement and transitions.",
      stage5_title: "Audio",
      stage5_desc: "ElevenLabs dialogue + Suno score. Per-character voice bibles, full cue sheet.",
      stage6_title: "Post & Delivery",
      stage6_desc: "DaVinci edit + Teal&Orange grade + Topaz 4K upscale. 4K master out.",
      pipe_foot: "The full chain, with the reasoning behind each choice, is in",
      qs_title: "Quick start",
      qs_sub: "Two ways in. Docker to look, source to work.",
      qs_tab_source: "Local Source",
      qs_docker_lede: "Fastest look. Backend, worker, Postgres, Redis in one command.",
      qs_terminal: "Terminal",
      qs_docker_note: "ComfyUI and model weights aren't bundled (license + size). Pull them with <code>bash 08_Automation/deploy_comfyui.sh</code> on a GPU host.",
      qs_source_lede: "For actually making a film. Needs an NVIDIA GPU (RTX 4090 24GB recommended).",
      qs_source_note: "Every generation script takes <code>--dry-run</code>. Run it first — it prints the full plan without calling ComfyUI or cloud APIs.",
      qs_tutor_prompt: "New here? The",
      qs_tutor_link: "step-by-step tutorial",
      qs_tutor_suffix: "walks from an empty repo to a 4K master, one command at a time.",
      plat_title: "Web platform",
      plat_sub: "For team members who don't want a terminal.",
      plat_backend_title: "Backend API",
      plat_backend_desc: "FastAPI + SQLAlchemy + Celery. SSE push for real-time queue status.",
      ep_submit: "submit render",
      ep_sse: "SSE live status",
      ep_health: "DB + Redis",
      plat_backend_foot: "Interactive docs at <code>/docs</code> (Swagger) and <code>/redoc</code>.",
      plat_frontend_title: "Frontend Console",
      plat_frontend_desc: "React 18 + Vite + Ant Design Pro. Eleven routes, end-to-end typed.",
      route_dash: "health + queue + projects",
      route_queue: "SSE-driven render queue",
      route_wf: "YAML params + provider scoring",
      plat_frontend_foot: "— proxies to :8000.",
      sim_title: "Simulate mode",
      sim_desc: "is on by default — every service returns mock output, so the whole chain runs without a GPU. Flip <code>SIMULATE_MODE=false</code> on a GPU host to hit real backends.",
      film_title: "The film that proves it",
      film_sub: "Echo of the Singularity — not a demo reel, a finished short.",
      poster_label: "CASE STUDY",
      film_p1: "A complete AIGC short film lives in the repo as a worked example. Script, character bible, 24-shot storyboard, 29 keyframes, 24 video clips, voice bibles, cue sheet, EDL, color notes, mix notes, asset manifest, subtitles, credits, delivery specs — every artifact a reviewer would expect from a finished short.",
      film_p2: "The rendered video files themselves are not committed (large, several use NC-licensed model outputs). The paperwork is the reference — run the pipeline end-to-end to populate the actual media, then follow <code>assembly_guide.md</code> to lock the master.",
      film_cta: "Open the case study",
      docs_title: "Read the manual",
      docs_sub: "Every doc is bilingual. English primary, Chinese sidecar.",
      doc_tag_tutorial: "TUTORIAL",
      doc_tutorial_title: "Step-by-step Tutorial",
      doc_tutorial_desc: "From empty repo to 4K master, one command at a time.",
      doc_tag_design: "DESIGN",
      doc_design_title: "AIGC Experience Chain",
      doc_design_desc: "End-to-end pipeline reasoning, stage by stage.",
      doc_tag_contrib: "CONTRIB",
      doc_contrib_title: "Contributing",
      doc_contrib_desc: "Push rules, monthly health check, translation flow.",
      doc_tag_ops: "OPS",
      doc_ops_title: "Troubleshooting",
      doc_ops_desc: "ComfyUI nodes, VRAM, model loaders, render queue.",
      doc_tag_budget: "BUDGET",
      doc_budget_title: "Cost Analysis",
      doc_budget_desc: "6-week budget, hardware, APIs, commercial upgrade path.",
      doc_tag_blog: "BLOG",
      doc_blog_title: "Architecture Notes",
      doc_blog_desc: "Why the queue is state-machine, why YAML-driven workflows.",
      doc_tag_security: "SECURITY",
      doc_security_title: "Security Policy",
      doc_security_desc: "Supported versions, reporting a vulnerability.",
      doc_tag_i18n: "I18N",
      doc_i18n_title: "Multilingual Index",
      doc_i18n_desc: "Bilingual doc table, naming convention, translation flow.",
      footer_tag: "Script in, 4K master out.",
      footer_repo: "Repo",
      footer_issues: "Issues",
      footer_prs: "Pull Requests",
      footer_start: "Start Here",
      footer_tutorial: "Tutorial",
      footer_qs: "Quick Start",
      footer_license_h: "License",
      footer_license_note: "Free to use, modify, and distribute. See LICENSE for details.",
      footer_credit: "The example film <i>Echo of the Singularity</i> is case-study content. Built on ComfyUI / Flux.1 / Wan2.2 / FastAPI / React."
    },
    zh: {
      title: "ShotFlow — 剧本输入，4K母版输出",
      meta_description: "一条可复现的 AIGC 短片制作流水线。从剧本到4K母版，每个参数都有记录。",
      skip_to_content: "跳到主要内容",
      nav_pipeline: "流水线",
      nav_quickstart: "快速开始",
      nav_platform: "平台",
      nav_film: "样片",
      nav_docs: "文档",
      nav_github: "GitHub ↗",
      hero_badge: "AIGC 短片制作流水线",
      hero_title: "ShotFlow",
      hero_tagline: "剧本输入，4K母版输出。",
      hero_desc: "一条可复现的 AIGC 短片制作流水线。24个镜头，29张关键帧，一部4K母版——每个参数都有记录，每次拍摄都能复现。",
      hero_cta_primary: "在 GitHub 查看",
      hero_cta_secondary: "GitCode 镜像",
      hero_cta_tertiary: "快速开始 ↓",
      stat_shots: "镜头",
      stat_keyframes: "关键帧",
      stat_tests: "测试用例",
      stat_master: "母版",
      scroll_hint: "向下滚动探索",
      prob_title: "解决什么问题",
      prob_sub: "每部 AIGC 短片都会遇到的那些墙。",
      prob1_title: "角色漂移",
      prob1_desc: "同一个角色在每个镜头里看起来都像不同的人。参考图漂移、锚点滑动、人脸重新生成。",
      prob2_title: "运动伪影",
      prob2_desc: "画面闪烁、扭曲，物体以不该有的方式运动。手指融合、边缘呼吸、物理规则失控。",
      prob3_title: "提示词漂移",
      prob3_desc: "提示词和故事板逐渐脱节，问题只在剪辑时才暴露——而此时一半镜头已经渲染完成。",
      prob4_title: "参数丢失",
      prob4_desc: "参数在会话间消失。那一次好的拍摄永远无法重现，因为没人记得当时用了什么参数。",
      prob5_title: "文件混乱",
      prob5_desc: "文件被重命名、覆盖、丢失。小团队花在找素材上的时间比做素材还多。",
      resolve_title: "ShotFlow 把一切串起来",
      resolve_desc: "一条流水线让结果可复现，让团队真正协作。是模板，不是产品——换个故事就能开拍。",
      pipe_title: "制作流水线",
      pipe_sub: "六个阶段，一条参数链，一部母版。",
      stage1_title: "剧本与世界观",
      stage1_desc: "DeepSeek / Claude。剧本、世界观构建、角色设定。",
      stage2_title: "关键帧",
      stage2_desc: "Flux.1 Kontext + IPAdapter。29张参考帧，角色保持一致。",
      stage3_title: "标准镜头",
      stage3_desc: "Wan2.2 I2V 14B。19个图生视频片段，用于对话和特写。",
      stage4_title: "复杂镜头",
      stage4_desc: "Kling 2.5 Turbo。5个关键帧到关键帧的镜头，用于运动和转场。",
      stage5_title: "音频",
      stage5_desc: "ElevenLabs 对白 + Suno 配乐。每个角色独立声库，完整配乐表。",
      stage6_title: "后期与交付",
      stage6_desc: "DaVinci 剪辑 + 青橙调色 + Topaz 4K 超分。输出4K母版。",
      pipe_foot: "完整的流程选择和设计思路请见",
      qs_title: "快速开始",
      qs_sub: "两种方式。用 Docker 看效果，用源码做片子。",
      qs_tab_source: "本地源码",
      qs_docker_lede: "最快体验方式。一条命令启动后端、工作节点、Postgres、Redis。",
      qs_terminal: "终端",
      qs_docker_note: "ComfyUI 和模型权重未打包（许可问题 + 体积大）。在有 GPU 的主机上运行 <code>bash 08_Automation/deploy_comfyui.sh</code> 拉取。",
      qs_source_lede: "真正做片子用。需要 NVIDIA GPU（推荐 RTX 4090 24GB）。",
      qs_source_note: "每个生成脚本都支持 <code>--dry-run</code>。先跑一遍——它会打印完整计划，不会调用 ComfyUI 或云端 API。",
      qs_tutor_prompt: "刚来？这里有",
      qs_tutor_link: "分步教程",
      qs_tutor_suffix: "从空仓库到4K母版，一条命令一条命令地带你走。",
      plat_title: "Web 平台",
      plat_sub: "给不想用终端的团队成员。",
      plat_backend_title: "后端 API",
      plat_backend_desc: "FastAPI + SQLAlchemy + Celery。SSE 推送实时队列状态。",
      ep_submit: "提交渲染",
      ep_sse: "SSE 实时状态",
      ep_health: "数据库 + Redis",
      plat_backend_foot: "交互式文档在 <code>/docs</code>（Swagger）和 <code>/redoc</code>。",
      plat_frontend_title: "前端控制台",
      plat_frontend_desc: "React 18 + Vite + Ant Design Pro。11个路由，端到端类型安全。",
      route_dash: "健康状态 + 队列 + 项目",
      route_queue: "SSE 驱动的渲染队列",
      route_wf: "YAML 参数 + 提供商评分",
      plat_frontend_foot: "— 代理到 :8000。",
      sim_title: "模拟模式",
      sim_desc: "默认开启——每个服务都返回模拟输出，整条链没有 GPU 也能跑。在有 GPU 的主机上设置 <code>SIMULATE_MODE=false</code> 调用真实后端。",
      film_title: "验证它的样片",
      film_sub: "《奇点回响》——不是演示片，是完成的短片。",
      poster_label: "案例研究",
      film_p1: "仓库里有一部完整的 AIGC 短片作为实例。剧本、角色设定、24镜故事板、29张关键帧、24段视频、声库、配乐表、EDL、调色笔记、混音笔记、素材清单、字幕、演职员表、交付规格——审核者对一部完成短片期望的所有工件都在。",
      film_p2: "渲染好的视频文件本身没有提交（体积大，部分使用 NC 许可的模型输出）。文档是参考——端到端跑一遍流水线生成实际媒体，然后按照 <code>assembly_guide.md</code> 锁定母版。",
      film_cta: "打开案例研究",
      docs_title: "阅读文档",
      docs_sub: "所有文档都是双语的。英文为主，中文对照。",
      doc_tag_tutorial: "教程",
      doc_tutorial_title: "分步教程",
      doc_tutorial_desc: "从空仓库到4K母版，一步一步来。",
      doc_tag_design: "设计",
      doc_design_title: "AIGC 体验链",
      doc_design_desc: "端到端流水线设计思路，逐阶段讲解。",
      doc_tag_contrib: "贡献",
      doc_contrib_title: "贡献指南",
      doc_contrib_desc: "推送规则、月度健康检查、翻译流程。",
      doc_tag_ops: "运维",
      doc_ops_title: "故障排查",
      doc_ops_desc: "ComfyUI 节点、显存、模型加载器、渲染队列。",
      doc_tag_budget: "预算",
      doc_budget_title: "成本分析",
      doc_budget_desc: "6周预算、硬件、API、商业化升级路径。",
      doc_tag_blog: "博客",
      doc_blog_title: "架构笔记",
      doc_blog_desc: "为什么队列是状态机，为什么工作流是 YAML 驱动的。",
      doc_tag_security: "安全",
      doc_security_title: "安全政策",
      doc_security_desc: "支持版本、漏洞上报。",
      doc_tag_i18n: "国际化",
      doc_i18n_title: "多语言索引",
      doc_i18n_desc: "双语文档表、命名规范、翻译流程。",
      footer_tag: "剧本输入，4K母版输出。",
      footer_repo: "仓库",
      footer_issues: "问题反馈",
      footer_prs: "拉取请求",
      footer_start: "从这里开始",
      footer_tutorial: "教程",
      footer_qs: "快速开始",
      footer_license_h: "许可证",
      footer_license_note: "自由使用、修改、分发。详见 LICENSE。",
      footer_credit: "样片《奇点回响》是案例研究内容。基于 ComfyUI / Flux.1 / Wan2.2 / FastAPI / React 构建。"
    }
  };

  function applyLang(lang) {
    if (!i18n[lang]) return;
    const dict = i18n[lang];
    document.documentElement.setAttribute('lang', lang === 'zh' ? 'zh-CN' : 'en');
    document.documentElement.setAttribute('data-lang', lang);
    
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      if (dict[key] !== undefined) {
        if (el.tagName === 'TITLE') {
          document.title = dict[key];
        } else if (el.tagName === 'META') {
          el.setAttribute('content', dict[key]);
        } else {
          el.innerHTML = dict[key];
        }
      }
    });

    document.querySelectorAll('.lang-option').forEach(function (opt) {
      opt.classList.toggle('active', opt.getAttribute('data-lang-code') === lang);
    });

    try { localStorage.setItem('shotflow-lang', lang); } catch(e) {}
  }

  var savedLang = 'en';
  try { savedLang = localStorage.getItem('shotflow-lang') || 'en'; } catch(e) {}
  if (savedLang !== 'en' && savedLang !== 'zh') savedLang = 'en';

  document.addEventListener('DOMContentLoaded', function () {
    applyLang(savedLang);

    var langToggle = document.getElementById('langToggle');
    if (langToggle) {
      langToggle.addEventListener('click', function (e) {
        var opt = e.target.closest('.lang-option');
        if (!opt) return;
        applyLang(opt.getAttribute('data-lang-code'));
      });
    }

    var tabs = document.querySelectorAll('.qs-tab');
    var panels = document.querySelectorAll('.qs-panel');
    function activateTab(name) {
      tabs.forEach(function (t) {
        var isActive = t.getAttribute('data-tab') === name;
        t.classList.toggle('qs-tab--active', isActive);
        t.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      panels.forEach(function (p) {
        p.classList.toggle('qs-panel--active', p.getAttribute('data-panel') === name);
      });
    }
    tabs.forEach(function (t) {
      t.addEventListener('click', function () { activateTab(t.getAttribute('data-tab')); });
    });

    var nav = document.getElementById('nav');
    if (nav) {
      function onScroll() {
        if (window.scrollY > 40) {
          nav.classList.add('scrolled');
        } else {
          nav.classList.remove('scrolled');
        }
      }
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }

    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener('click', function (e) {
        var href = a.getAttribute('href');
        if (href === '#') return;
        var target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  });
})();
