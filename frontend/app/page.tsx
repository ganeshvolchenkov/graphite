"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { 
  Terminal, Activity, ShieldAlert, Cpu, CheckCircle2, ChevronRight, ChevronLeft,
  BarChart3, Database, AlertTriangle, Zap, Server, Code, FileWarning, 
  TrendingDown, TrendingUp, Lock, ArrowRight, Play, RefreshCw, Network,
  BrainCircuit, Globe2, GaugeCircle, Rocket, EyeOff, Zap as ZapFast, Shapes
} from "lucide-react";

export default function Presentation() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [direction, setDirection] = useState(0);
  const totalSlides = 7;

  const paginate = useCallback((newDirection: number) => {
    setDirection(newDirection);
    setCurrentSlide((prev) => {
      const next = prev + newDirection;
      if (next < 0) return 0;
      if (next >= totalSlides) return totalSlides - 1;
      return next;
    });
  }, [totalSlides]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        paginate(1);
      } else if (e.key === 'ArrowLeft') {
        paginate(-1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [paginate]);

  const slides = [
    <Slide0 key="s0" />,
    <Slide1 key="s1" />,
    <Slide2 key="s2" />,
    <Slide3 key="s3" />,
    <Slide4 key="s4" />,
    <Slide5 key="s5" />,
    <Slide6 key="s6" />
  ];

  const variants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 1000 : -1000,
      opacity: 0,
      scale: 0.9,
      rotateY: direction > 0 ? 15 : -15,
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
      scale: 1,
      rotateY: 0,
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction < 0 ? 1000 : -1000,
      opacity: 0,
      scale: 0.9,
      rotateY: direction < 0 ? 15 : -15,
    })
  };

  return (
    <div className="h-screen w-screen bg-[#020202] text-zinc-300 font-sans overflow-hidden flex flex-col font-light selection:bg-emerald-500/30 relative perspective-1000">
      
      {/* Dynamic Animated Background */}
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none mix-blend-overlay z-0" />
      <motion.div 
        animate={{ 
          scale: [1, 1.2, 1], 
          opacity: [0.1, 0.2, 0.1],
          x: [0, 100, 0] 
        }} 
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
        className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] rounded-full bg-emerald-900/30 blur-[150px] pointer-events-none" 
      />
      <motion.div 
        animate={{ 
          scale: [1, 1.3, 1], 
          opacity: [0.1, 0.25, 0.1],
          x: [0, -100, 0] 
        }} 
        transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
        className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-cyan-900/30 blur-[150px] pointer-events-none" 
      />

      {/* Header */}
      <motion.nav 
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.8 }}
        className="fixed top-0 left-0 right-0 p-8 flex justify-between items-center z-50 pointer-events-none"
      >
        <div className="flex items-center gap-3 font-mono font-bold text-white text-2xl tracking-tighter">
          <motion.div 
            whileHover={{ rotate: 180 }}
            transition={{ duration: 0.5 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.4)]"
          >
            <Activity className="text-black" size={24} />
          </motion.div>
          Graphite
        </div>
        <div className="flex items-center gap-4">
          <div className="px-4 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.05] text-xs font-mono text-zinc-400 backdrop-blur-md">
            Accel AI Innovate: Amsterdam
          </div>
          <div className="w-12 h-12 rounded-full bg-white/[0.03] border border-white/[0.05] flex items-center justify-center font-mono text-sm text-white backdrop-blur-md shadow-inner">
            {currentSlide + 1}<span className="text-zinc-600">/7</span>
          </div>
        </div>
      </motion.nav>

      {/* Main Slide Content */}
      <main className="flex-1 flex items-center justify-center relative w-full h-full z-10 perspective-1000">
        <AnimatePresence custom={direction} mode="wait">
          <motion.div
            key={currentSlide}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{
              x: { type: "spring", stiffness: 250, damping: 30 },
              opacity: { duration: 0.4 },
              scale: { duration: 0.5 },
              rotateY: { duration: 0.5 }
            }}
            className="absolute inset-0 flex items-center justify-center transform-gpu"
          >
            <div className="w-full max-w-7xl px-12">
               {slides[currentSlide]}
            </div>
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Progress Bar */}
      <div className="fixed bottom-0 left-0 h-1 bg-white/5 w-full z-50">
        <motion.div 
          className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500"
          initial={{ width: 0 }}
          animate={{ width: `${((currentSlide + 1) / totalSlides) * 100}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />
      </div>

      {/* Slide Controls */}
      <div className="fixed bottom-8 right-8 flex gap-4 z-50">
        <motion.button 
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => paginate(-1)} 
          disabled={currentSlide === 0} 
          className="p-4 bg-white/5 border border-white/10 rounded-full disabled:opacity-20 disabled:hover:scale-100 transition-colors text-white backdrop-blur-md"
        >
          <ChevronLeft size={24} />
        </motion.button>
        <motion.button 
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => paginate(1)} 
          disabled={currentSlide === totalSlides - 1} 
          className="p-4 bg-white/5 border border-white/10 rounded-full disabled:opacity-20 disabled:hover:scale-100 transition-colors text-white backdrop-blur-md shadow-[0_0_20px_rgba(255,255,255,0.05)]"
        >
          <ChevronRight size={24} />
        </motion.button>
      </div>

    </div>
  );
}

// -------------------------------------------------------------
// Slide Components
// -------------------------------------------------------------

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.2, delayChildren: 0.1 }
  }
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } }
};

const Slide0 = () => (
  <motion.div 
    variants={containerVariants} initial="hidden" animate="show"
    className="text-center space-y-10 flex flex-col items-center"
  >
    <motion.div 
      variants={itemVariants}
      className="inline-flex items-center gap-3 px-6 py-2.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono text-sm shadow-[0_0_30px_rgba(16,185,129,0.3)] relative overflow-hidden"
    >
      <motion.div 
        animate={{ x: ["-100%", "200%"] }} 
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        className="absolute inset-0 w-1/3 bg-gradient-to-r from-transparent via-emerald-400/20 to-transparent skew-x-12"
      />
      <Zap size={18} className="text-emerald-300" /> 
      Nebius Token Factory
    </motion.div>
    
    <motion.h1 
      variants={itemVariants}
      className="text-7xl md:text-[100px] font-extrabold tracking-tighter text-white max-w-6xl mx-auto leading-[1.1] drop-shadow-2xl"
    >
      Stop backtesting <br/> on the past. <br />
      <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-cyan-400 to-emerald-300">
        Stress-test the unknown.
      </span>
    </motion.h1>
    
    <motion.p 
      variants={itemVariants}
      className="text-3xl text-zinc-400 max-w-4xl mx-auto leading-relaxed font-light"
    >
      An AI-driven quantitative market simulator & code auditor for future founders.
    </motion.p>
  </motion.div>
);

const Slide1 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-16 max-w-6xl mx-auto flex flex-col items-center text-center">
    <motion.div variants={itemVariants} className="flex flex-col items-center gap-6">
      <motion.div 
        animate={{ rotate: [-5, 5, -5] }} 
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        className="p-6 bg-red-500/10 rounded-full border border-red-500/20 shadow-[0_0_50px_rgba(239,68,68,0.3)]"
      >
        <TrendingDown size={64} className="text-red-500" />
      </motion.div>
      <h2 className="text-6xl font-bold text-white tracking-tight">Our Story: The Breaking Point</h2>
    </motion.div>

    <motion.div variants={itemVariants} className="text-2xl text-zinc-300 max-w-4xl leading-relaxed space-y-8 font-light">
      <p>
        We built quantitative algorithms relying on massive sets of historical data. We thought we were resilient.
      </p>
      <motion.div 
        className="p-8 bg-gradient-to-r from-red-950/40 to-transparent border-l-4 border-red-500 rounded-r-2xl text-left"
        initial={{ opacity: 0, x: -50 }} whileInView={{ opacity: 1, x: 0 }} transition={{ duration: 0.8 }}
      >
        <p className="text-white font-medium text-3xl mb-4">Then a Black Swan event hit.</p>
        <p className="text-red-300">Liquidity evaporated instantly. Order books crossed. Our backtests completely failed to predict how our code would react to <strong className="text-white">unprecedented market microstructure breakdowns.</strong></p>
      </motion.div>
      <p>
        We realized: <span className="text-white font-medium">You cannot backtest against a future that hasn't happened yet.</span>
      </p>
    </motion.div>
  </motion.div>
);

const Slide2 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-16 max-w-7xl mx-auto">
    <motion.div variants={itemVariants} className="text-center">
      <h2 className="text-6xl font-bold text-white tracking-tight mb-6">The Open-Weight Advantage</h2>
      <p className="text-2xl text-zinc-400 font-light">Why we chose <strong className="text-emerald-400">Nebius Token Factory</strong> over closed APIs.</p>
    </motion.div>

    <div className="grid md:grid-cols-3 gap-8">
      <motion.div 
        variants={itemVariants}
        whileHover={{ y: -10, scale: 1.02 }}
        className="bg-gradient-to-br from-cyan-950/30 to-black border border-cyan-900/30 p-10 rounded-3xl relative overflow-hidden shadow-[0_0_40px_rgba(6,182,212,0.1)]"
      >
        <EyeOff size={48} className="text-cyan-400 mb-6" />
        <h3 className="text-3xl font-bold text-white mb-4">Absolute Privacy</h3>
        <p className="text-zinc-400 text-lg leading-relaxed">
          Quant strategies are highly proprietary. Sending raw trading logic and alpha to closed APIs is a non-starter. Open-weight models ensure our intellectual property never leaves our control.
        </p>
      </motion.div>

      <motion.div 
        variants={itemVariants}
        whileHover={{ y: -10, scale: 1.02 }}
        className="bg-gradient-to-b from-purple-950/30 to-black border border-purple-900/30 p-10 rounded-3xl relative overflow-hidden shadow-[0_0_40px_rgba(168,85,247,0.1)]"
      >
        <Shapes size={48} className="text-purple-400 mb-6" />
        <h3 className="text-3xl font-bold text-white mb-4">Grammar Forcing</h3>
        <p className="text-zinc-400 text-lg leading-relaxed">
          We need deterministic JSON order book events, not prose. Open-weight models give us the lower-level access required to strictly force output grammar, eliminating hallucinations in our tape.
        </p>
      </motion.div>

      <motion.div 
        variants={itemVariants}
        whileHover={{ y: -10, scale: 1.02 }}
        className="bg-gradient-to-bl from-emerald-950/30 to-black border border-emerald-900/30 p-10 rounded-3xl relative overflow-hidden shadow-[0_0_40px_rgba(16,185,129,0.1)]"
      >
        <ZapFast size={48} className="text-emerald-400 mb-6" />
        <h3 className="text-3xl font-bold text-white mb-4">Raw Inference Speed</h3>
        <p className="text-zinc-400 text-lg leading-relaxed">
          Generating millisecond-resolution L2 depth data requires massive token throughput. Nebius infrastructure allows us to generate 15,000+ synthetic ticks per second effortlessly.
        </p>
      </motion.div>
    </div>
  </motion.div>
);

const Slide3 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-16 max-w-6xl mx-auto flex flex-col items-center text-center">
    <motion.div 
      variants={itemVariants}
      animate={{ 
        boxShadow: ["0px 0px 40px rgba(16,185,129,0.2)", "0px 0px 80px rgba(16,185,129,0.6)", "0px 0px 40px rgba(16,185,129,0.2)"] 
      }}
      transition={{ duration: 4, repeat: Infinity }}
      className="p-8 bg-black rounded-[2rem] border border-emerald-500/30"
    >
      <BrainCircuit size={80} className="text-emerald-400" />
    </motion.div>
    
    <motion.h2 variants={itemVariants} className="text-7xl font-bold text-white tracking-tight">Meet Graphite</motion.h2>
    
    <motion.p variants={itemVariants} className="text-3xl text-zinc-300 leading-relaxed max-w-4xl font-light">
      We built an AI engine that <strong className="text-emerald-400 font-semibold text-4xl">hallucinates the unknown.</strong>
    </motion.p>

    <motion.div variants={itemVariants} className="grid md:grid-cols-2 gap-6 w-full mt-8">
      <div className="flex items-center gap-6 p-8 bg-white/[0.02] border border-white/[0.05] rounded-3xl backdrop-blur-xl text-left">
        <Database size={40} className="text-cyan-400 shrink-0" />
        <p className="text-xl text-zinc-300">Translates natural language macro scenarios into deterministic order book data.</p>
      </div>
      <div className="flex items-center gap-6 p-8 bg-white/[0.02] border border-white/[0.05] rounded-3xl backdrop-blur-xl text-left">
        <ShieldAlert size={40} className="text-emerald-400 shrink-0" />
        <p className="text-xl text-zinc-300">Audits logic against extreme volatility and auto-generates defensive code refactors.</p>
      </div>
    </motion.div>
  </motion.div>
);

const Slide4 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-12 max-w-7xl mx-auto">
    <motion.div variants={itemVariants} className="text-center mb-16">
      <h2 className="text-6xl font-bold text-white tracking-tight mb-4">The Execution Engine</h2>
      <p className="text-2xl text-zinc-400 font-light">A seamless pipeline powered by DeepSeek-V4-Pro.</p>
    </motion.div>
    
    <div className="flex flex-col md:flex-row items-stretch gap-8 relative">
      {/* Animated connecting line */}
      <div className="absolute top-1/2 left-[20%] right-[20%] h-1 hidden md:block -z-10 overflow-hidden rounded-full bg-white/5">
        <motion.div 
          animate={{ x: ["-100%", "200%"] }} 
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          className="w-1/2 h-full bg-gradient-to-r from-transparent via-emerald-400 to-transparent"
        />
      </div>
      
      <motion.div variants={itemVariants} className="flex-1 bg-black/80 backdrop-blur-2xl border border-white/10 p-12 rounded-[2rem] relative shadow-2xl">
        <div className="absolute -top-8 left-12 p-6 bg-cyan-950 rounded-3xl text-cyan-400 border border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.3)]">
          <Database size={48} />
        </div>
        <h3 className="text-4xl font-bold text-white mt-8 mb-6">Phase 1: Generator</h3>
        <p className="text-xl text-zinc-400 mb-8 leading-relaxed font-light">
          We prompt the model with an abstract macro event. It forces deterministic output, generating thousands of JSON tick events representing toxic flow cascades.
        </p>
        <div className="bg-[#0a0a0a] p-6 rounded-2xl font-mono text-sm text-zinc-300 border border-white/5 shadow-inner">
          <span className="text-zinc-500">&gt; Prompt:</span> "Flash crash, 0 liquidity"<br/>
          <motion.span 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1, duration: 1 }}
            className="text-cyan-400 mt-2 block font-bold"
          >
            &gt; Output: 15,000 JSON ticks generated.
          </motion.span>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="hidden md:flex items-center justify-center relative">
        <motion.div animate={{ x: [0, 10, 0] }} transition={{ duration: 1.5, repeat: Infinity }}>
          <div className="p-5 bg-emerald-500/20 rounded-full border border-emerald-500/30 text-emerald-400 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
            <ArrowRight size={36} />
          </div>
        </motion.div>
      </motion.div>

      <motion.div variants={itemVariants} className="flex-1 bg-black/80 backdrop-blur-2xl border border-white/10 p-12 rounded-[2rem] relative shadow-2xl">
        <div className="absolute -top-8 left-12 p-6 bg-emerald-950 rounded-3xl text-emerald-400 border border-emerald-500/50 shadow-[0_0_30px_rgba(16,185,129,0.3)]">
          <Code size={48} />
        </div>
        <h3 className="text-4xl font-bold text-white mt-8 mb-6">Phase 2: Auditor</h3>
        <p className="text-xl text-zinc-400 mb-8 leading-relaxed font-light">
          Our backend engine compiles your algorithm, pipes the synthetic tape through it, catches catastrophic exceptions, and asks the LLM for a defensive Git Diff.
        </p>
        <div className="bg-[#0a0a0a] p-6 rounded-2xl font-mono text-sm text-zinc-300 border border-white/5 shadow-inner">
          <span className="text-red-400 font-bold">&gt; Exception: Line 7 ZeroDivisionError</span><br/>
          <motion.span 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2, duration: 1 }}
            className="text-emerald-400 mt-2 block font-bold"
          >
            &gt; Fix: + if volume == 0: return 0
          </motion.span>
        </div>
      </motion.div>
    </div>
  </motion.div>
);

const Slide5 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="h-full flex flex-col justify-center max-w-7xl mx-auto py-8 w-full items-center text-center space-y-6">
    <motion.div variants={itemVariants} className="flex justify-between w-full max-w-6xl items-end">
      <div className="text-left">
        <h2 className="text-5xl font-bold text-white tracking-tight mb-2">Live Platform Demo</h2>
        <p className="text-xl text-zinc-400 font-light">Interact with Graphite directly.</p>
      </div>
      <a 
        href="https://graphite-ai.lovable.app/" 
        target="_blank" 
        rel="noopener noreferrer"
        className="px-6 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-full font-bold flex items-center gap-2 transition-all border border-emerald-500/30 hover:scale-105"
      >
        Launch External <ArrowRight size={18} />
      </a>
    </motion.div>
    
    <motion.div 
      variants={itemVariants}
      className="relative w-full max-w-6xl h-[65vh] rounded-2xl border border-white/10 shadow-[0_0_150px_rgba(16,185,129,0.2)] bg-[#050505] overflow-hidden flex items-center justify-center group"
    >
      <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 via-transparent to-cyan-500/5 opacity-50 pointer-events-none" />
      <iframe 
        src="https://graphite-ai.lovable.app/" 
        className="w-full h-full relative z-10 border-0"
        title="Graphite App"
        allow="clipboard-write"
      />
    </motion.div>
  </motion.div>
);

const Slide6 = () => (
  <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-16 max-w-6xl mx-auto text-center">
    <motion.div variants={itemVariants}>
      <div className="inline-flex p-6 bg-purple-500/10 rounded-full border border-purple-500/30 shadow-[0_0_60px_rgba(168,85,247,0.3)] mb-6">
        <Rocket size={64} className="text-purple-400" />
      </div>
      <h2 className="text-7xl font-bold text-white tracking-tight">Company Potential</h2>
      <p className="text-3xl text-zinc-400 font-light mt-4">From a hackathon prototype to an enterprise standard.</p>
    </motion.div>
    
    <div className="space-y-6 text-left mt-16 max-w-4xl mx-auto">
      <motion.div variants={itemVariants} whileHover={{ scale: 1.03, x: 10 }} className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-8 rounded-[2rem] flex items-center gap-8 shadow-2xl transition-all cursor-pointer hover:border-emerald-500/30 hover:bg-emerald-500/5">
        <div className="p-6 bg-emerald-900/20 text-emerald-400 rounded-2xl border border-emerald-500/30">
          <Network size={40} />
        </div>
        <div>
          <h3 className="text-3xl font-bold text-white mb-2">Live FIX Engine Integration</h3>
          <p className="text-xl text-zinc-400 font-light">Pipe our synthetic scenarios directly into institutional HFT trading environments.</p>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} whileHover={{ scale: 1.03, x: 10 }} className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-8 rounded-[2rem] flex items-center gap-8 shadow-2xl transition-all cursor-pointer hover:border-cyan-500/30 hover:bg-cyan-500/5">
        <div className="p-6 bg-cyan-900/20 text-cyan-400 rounded-2xl border border-cyan-500/30">
          <BrainCircuit size={40} />
        </div>
        <div>
          <h3 className="text-3xl font-bold text-white mb-2">Multi-Agent AI Simulations</h3>
          <p className="text-xl text-zinc-400 font-light">Adversarial LLM agents acting as market makers, competing against the user's algorithms in real-time.</p>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} whileHover={{ scale: 1.03, x: 10 }} className="bg-white/[0.02] backdrop-blur-xl border border-white/5 p-8 rounded-[2rem] flex items-center gap-8 shadow-2xl transition-all cursor-pointer hover:border-purple-500/30 hover:bg-purple-500/5">
        <div className="p-6 bg-purple-900/20 text-purple-400 rounded-2xl border border-purple-500/30">
          <ShieldAlert size={40} />
        </div>
        <div>
          <h3 className="text-3xl font-bold text-white mb-2">Automated CI/CD Pipeline Linter</h3>
          <p className="text-xl text-zinc-400 font-light">Block GitHub pull requests if quant algorithms fail a synthetic market shock test.</p>
        </div>
      </motion.div>
    </div>
  </motion.div>
);
