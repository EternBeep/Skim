"""
VibeSeek - Week 1 (storage updated in Week 2)
CLIP Embedder: Generates visual embeddings for frames and text queries.
Uses OpenAI's CLIP (via the `clip` package) to encode both images and text
into the same 512-dim vector space — enabling semantic similarity search.

Week 2 note: persistence moved from the pickled VideoIndex to ChromaDB
(see vector_store.py). This module now only produces embeddings; FrameEmbedding
is the lightweight carrier handed off to the vector store.
"""

import os #helps to work w the os
import numpy as np #used for numerical operations
import torch #used for numerical operations
import clip #used for numerical operations, CLIP-Contrastive Language-Image Pretraining
from PIL import Image#used to open the video
from pathlib import Path #used to work w the path
from dataclasses import dataclass #dataclass is use to creat a cleaner function style instead of the original one

from frame_extractor import Frame#this is used to get the frames from the video

#used to store the frames
@dataclass #dataclass is use to creat a cleaner function style instead of the original one
class FrameEmbedding: #this is used to store the frames
    frame: Frame #this is used to store the frames
    embedding: np.ndarray          # shape: (512,) float32, L2-normalised


class CLIPEmbedder: #used to encode the frames
    """
    Wraps CLIP model for image and text encoding.

    Usage:
        embedder = CLIPEmbedder()
        frame_embeddings = embedder.embed_frames(frames)
        query_vec = embedder.embed_text("the beat drop")
        results = embedder.search(query_vec, frame_embeddings, top_k=5)
    """

    def __init__(self, model_name: str = "ViT-B/32", device: str = None): #model_name is the name of the model used to encode the frames
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")#this is used to check if the model is available on the GPU or CPU and load it in the same
        print(f"[CLIPEmbedder] Loading CLIP {model_name} on {self.device}...")#this is used to print the model name and the device it is loaded on
        self.model, self.preprocess = clip.load(model_name, device=self.device)#this is used to load the model and the preprocess
        self.model.eval()#model in evaluation mode
        print(f"[CLIPEmbedder] Ready.")#this is used to print that the model is ready

    # ------------------------------------------------------------------ #
    #  Image encoding                                                      #
    # ------------------------------------------------------------------ #

    def embed_frames(
        self,
        frames: list[Frame],
        batch_size: int = 16,           # Week 3: 16 keeps peak RAM low for CPU-only hosts
        show_progress: bool = True,
    ) -> list[FrameEmbedding]:
        """
        Encodes a list of Frame objects into normalised CLIP embeddings.
        Processes in batches for efficiency.
        """
        results: list[FrameEmbedding] = [] #this is used to store the frames
        total = len(frames)#this is used to get the total number of frames

        for batch_start in range(0, total, batch_size):#this is used to get the number of frames in each batch
            batch = frames[batch_start: batch_start + batch_size]#this is used to get the frames in each batch

            images = []#this is used to store the frames
            valid_frames = [] #this is used to store the valid frames
            for frame in batch: #this is used to iterate through the frames in the batch 
                try:
                    img = Image.open(frame.image_path).convert("RGB")#this is used to open the frame and convert it to RGB
                    images.append(self.preprocess(img))#this is used to preprocess the frame
                    valid_frames.append(frame)#this is used to add the frame to the list of valid frames
                except Exception as e:  #this is used to catch any exceptions that may occur
                    print(f"[CLIPEmbedder] Skipping {frame.image_path}: {e}")

            if not images: #this is used to check if there are any images to process
                continue

            image_tensor = torch.stack(images).to(self.device)#this is used to stack the frames and move them to the device

            with torch.no_grad():#this is used to prevent the calculation of gradients
                features = self.model.encode_image(image_tensor)#this is used to encode the image
                features = features / features.norm(dim=-1, keepdim=True)   # L2 norm
                features = features.cpu().numpy().astype(np.float32)#this is used to convert the features to numpy array and then to float32

            for frame, embedding in zip(valid_frames, features):#this is used to zip the valid frames and the features together
                results.append(FrameEmbedding(frame=frame, embedding=embedding))#this is used to append the frame embedding to the results

            if show_progress:#this is used to show the progress of the frame embedding
                done = min(batch_start + batch_size, total)#this is used to get the number of frames in the current batch
                print(f"[CLIPEmbedder] Embedded {done}/{total} frames...", end="\r")#this is used to print the progress of the frame embedding

        print(f"\n[CLIPEmbedder] Done — {len(results)} frame embeddings created.")#this is used to print the number of frames created
        return results

    # ------------------------------------------------------------------ #
    #  Text encoding                                                       #
    # ------------------------------------------------------------------ #

    def embed_text(self, query: str) -> np.ndarray:#this is used to encode the text query
        """
        Encodes a natural-language query string into a normalised CLIP embedding.
        Returns shape (512,) float32.
        """
        tokens = clip.tokenize([query]).to(self.device)#this is used to tokenize the query and move it to the device
        with torch.no_grad():#this is used to prevent the calculation of gradients
            features = self.model.encode_text(tokens)#this is used to encode the text
            features = features / features.norm(dim=-1, keepdim=True)#this is used to normalize the features 
        return features.cpu().numpy()[0].astype(np.float32)#this is used to convert the features to numpy array and then to float32

    # ------------------------------------------------------------------ #
    #  Cosine similarity search                                            #
    # ------------------------------------------------------------------ #

    def search(
        self,
        query_embedding: np.ndarray,
        frame_embeddings: list[FrameEmbedding],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Computes cosine similarity between query and all frame embeddings.
        Since vectors are already L2-normalised, cosine sim == dot product.

        Returns top_k results sorted by score (highest first):
            [{"timestamp": float, "score": float, "image_path": str}, ...]
        """
        if not frame_embeddings:
            return []

        # Stack all embeddings into a matrix: (N, 512)
        matrix = np.stack([fe.embedding for fe in frame_embeddings])#this is used to stack the embeddings into a matrix

        # Dot product = cosine similarity (both sides are unit vectors)
        scores = matrix @ query_embedding          # shape: (N,512) this is used to calculate the cosine similarity
#THIS IS MATRIX MULTIPLICATION
        # Get top-k indices sorted by score descending
        top_indices = np.argsort(scores)[::-1][:top_k] #its in reverse order and keep top_k results only
        results = []
        for idx in top_indices: #this is used to iterate through the top_k indices
            fe = frame_embeddings[idx]#this is used to get the frame embedding of the current index
            results.append({ #this is used to append the results
                "timestamp": fe.frame.timestamp,
                "score": float(scores[idx]),
                "image_path": fe.frame.image_path,
                "frame_index": fe.frame.frame_index,
            })

        return results
