import { motion } from "framer-motion";

export function AnimatedGridBackground() {
  return (
    <div className="animated-grid-bg">
      <div className="animated-grid-bg__static" />
      <motion.div
        className="animated-grid-bg__moving"
        animate={{
          backgroundPosition: ["0px 0px", "0px 40px"],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          ease: "linear"
        }}
      />
    </div>
  );
}
