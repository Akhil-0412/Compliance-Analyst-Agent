"use client";

import { motion } from "framer-motion";

export function ThinkingIndicator() {
    return (
        <div className="flex items-center space-x-2 text-cyan-400 text-sm font-mono mt-2">
            <motion.div
                className="relative w-4 h-4"
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
                <span className="absolute inset-0 border-2 border-cyan-400 border-t-transparent rounded-full" />
            </motion.div>
            <motion.span
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity }}
            >
                ANALYZING COMPLIANCE RISK...
            </motion.span>
        </div>
    );
}
