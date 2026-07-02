import { motion } from "framer-motion";

const STEPS = [
  {
    n: "01",
    title: "See + hear",
    desc: "OpenCV samples frames; Whisper transcribes the audio into timestamped lines",
  },
  {
    n: "02",
    title: "Dual embeddings",
    desc: "CLIP encodes each frame; MiniLM encodes each spoken line — two semantic spaces",
  },
  {
    n: "03",
    title: "Hybrid search",
    desc: "Your query hits both spaces; Reciprocal Rank Fusion blends seen + said into one ranking",
  },
];

export default function HowItWorks() {
  return (
    <motion.section
      className="card how-it-works"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="card__label">
        <span className="card__step">?</span>
        How Skim works
      </div>
      <div className="how-it-works__grid">
        {STEPS.map((s) => (
          <div key={s.n}>
            <div className="how-it-works__item-num">{s.n}</div>
            <div className="how-it-works__item-title">{s.title}</div>
            <div className="how-it-works__item-desc">{s.desc}</div>
          </div>
        ))}
      </div>
      <div className="how-it-works__footer">
        Vectors persist in Pinecone · thumbnails on Cloudinary · cached globally in Redis for instant repeat searches
      </div>
    </motion.section>
  );
}
