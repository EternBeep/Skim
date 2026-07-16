import { motion } from "framer-motion";

export function AuroraBackground() {
  return (
    <div className="aurora-bg">
      <div className="aurora-bg__noise" />
      
      {/* Blob 1 - Cyan */}
      <motion.div
        className="aurora-bg__blob aurora-bg__blob--1"
        animate={{
          x: [0, 50, 0],
          y: [0, 30, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          repeatType: "reverse",
          ease: "easeInOut"
        }}
      />
      
      {/* Blob 2 - Violet */}
      <motion.div
        className="aurora-bg__blob aurora-bg__blob--2"
        animate={{
          x: [0, -40, 0],
          y: [0, -50, 0],
          scale: [1, 1.2, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          repeatType: "reverse",
          ease: "easeInOut"
        }}
      />
      
      {/* Blob 3 - Blue */}
      <motion.div
        className="aurora-bg__blob aurora-bg__blob--3"
        animate={{
          x: [0, 30, 0],
          y: [0, -40, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 20,
          repeat: Infinity,
          repeatType: "reverse",
          ease: "easeInOut"
        }}
      />
    </div>
  );
}
