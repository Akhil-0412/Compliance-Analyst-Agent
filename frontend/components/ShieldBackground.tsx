"use client";

import { motion } from "framer-motion";
import React, { useEffect, useState } from "react";

type Particle = {
    x: number;
    y: number;
    duration: number;
    delay: number;
};

export function ShieldBackground() {
    const [particles, setParticles] = useState<Particle[]>([]);

    useEffect(() => {
        const generated = Array.from({ length: 20 }).map(() => ({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            duration: Math.random() * 5 + 5,
            delay: Math.random() * 5,
        }));

        setParticles(generated);
    }, []);

    return (
        <div className="fixed inset-0 z-0 bg-slate-950 overflow-hidden flex items-center justify-center pointer-events-none">

            {/* Dynamic Grid Background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20" />

            {/* Central Shield Pulse */}
            <motion.div
                className="relative flex items-center justify-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 1.5 }}
            >
                {/* Outer Ring */}
                <motion.div
                    className="absolute w-[800px] h-[800px] border border-cyan-500/20 rounded-full"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
                >
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-cyan-500/50 rounded-full shadow-[0_0_10px_#06b6d4]" />
                    <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 h-2 bg-cyan-500/50 rounded-full shadow-[0_0_10px_#06b6d4]" />
                </motion.div>

                {/* Middle Ring */}
                <motion.div
                    className="absolute w-[600px] h-[600px] border border-cyan-400/30 rounded-full border-dashed"
                    animate={{ rotate: -360 }}
                    transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                />

                {/* Inner Ring Pulse */}
                <motion.div
                    className="absolute w-[400px] h-[400px] border-2 border-cyan-500/10 rounded-full"
                    animate={{ scale: [1, 1.05, 1], opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                />

                {/* Core Glow */}
                <div className="absolute w-[200px] h-[200px] bg-cyan-500/5 blur-[100px] rounded-full" />
            </motion.div>

            {/* Tech Particles */}
            <div className="absolute inset-0">
                {particles.map((p, i) => (
                    <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-cyan-400/40 rounded-full"
                        initial={{ x: p.x, y: p.y, opacity: 0 }}
                        animate={{
                            y: [p.y, p.y - 100],
                            opacity: [0, 1, 0],
                        }}
                        transition={{
                            duration: p.duration,
                            repeat: Infinity,
                            ease: "linear",
                            delay: p.delay,
                        }}
                    />
                ))}
            </div>
        </div>
    );
}
