import { motion } from "framer-motion";

export function GlowingBorder({ children, className = "", duration = 4 }) {
  return (
    <div className={`glowing-border-wrapper ${className}`}>
      <span className="glowing-border-wrapper__spin" style={{ animationDuration: `${duration}s` }} />
      <div className="glowing-border-wrapper__inner">
        {children}
      </div>
    </div>
  );
}
