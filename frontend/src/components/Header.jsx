import { motion } from "framer-motion";
import { ScanLine } from "lucide-react";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, delay: i * 0.08, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function Header() {
  return (
    <header className="header">
      <motion.div
        className="header__badge"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <span className="header__badge-dot" aria-hidden="true" />
        <ScanLine size={12} aria-hidden="true" />
        Semantic video search
      </motion.div>

      <motion.h1
        className="header__title"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={1}
      >
        Skim
        <span className="header__title-accent">the moment</span>
      </motion.h1>

      <motion.p
        className="header__subtitle"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
        custom={2}
      >
        Paste a YouTube URL. Describe a vibe. Jump to that moment — by what was{" "}
        <em>seen</em> and what was <em>said</em>.
      </motion.p>
    </header>
  );
}
