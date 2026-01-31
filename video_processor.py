"""
SewerSentinel Video Frame Extractor
Extracts frames from CCTV inspection videos for analysis
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Extracts and processes frames from pipe inspection videos.

    Supports common video formats: mp4, avi, mov, mkv, wmv
    """

    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'}

    def __init__(
        self,
        frames_per_second: float = 1.0,
        max_dimension: int = 1024,
        output_format: str = "jpg",
        jpeg_quality: int = 85
    ):
        """
        Initialize the video processor.

        Args:
            frames_per_second: Number of frames to extract per second (default: 1.0)
            max_dimension: Maximum dimension (width or height) for resized frames
            output_format: Output image format (jpg or png)
            jpeg_quality: JPEG quality (1-100) if output_format is jpg
        """
        self.frames_per_second = frames_per_second
        self.max_dimension = max_dimension
        self.output_format = output_format.lower()
        self.jpeg_quality = jpeg_quality

        logger.info(f"VideoProcessor initialized: {frames_per_second} fps, max {max_dimension}px")

    def extract_frames(
        self,
        video_path: str,
        output_dir: Optional[str] = None
    ) -> Tuple[List[str], List[float]]:
        """
        Extract frames from a video file.

        Args:
            video_path: Path to the video file
            output_dir: Directory to save extracted frames (creates temp dir if None)

        Returns:
            Tuple of (list of frame file paths, list of timestamps in seconds)
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if video_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported video format: {video_path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="sewersentinel_frames_")
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_dir = Path(output_dir)
        logger.info(f"Extracting frames from {video_path} to {output_dir}")

        # Open video
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {video_path}")

        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            logger.info(f"Video: {fps:.2f} fps, {total_frames} frames, {duration:.2f} seconds")

            # Calculate frame interval
            frame_interval = int(fps / self.frames_per_second) if fps > 0 else 1
            frame_interval = max(1, frame_interval)

            frame_paths = []
            timestamps = []
            frame_count = 0
            extracted_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Extract frame at interval
                if frame_count % frame_interval == 0:
                    # Calculate timestamp
                    timestamp = frame_count / fps if fps > 0 else frame_count

                    # Resize frame
                    resized_frame = self._resize_frame(frame)

                    # Save frame
                    frame_filename = f"frame_{extracted_count:06d}.{self.output_format}"
                    frame_path = output_dir / frame_filename

                    if self.output_format == "jpg":
                        cv2.imwrite(
                            str(frame_path),
                            resized_frame,
                            [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                        )
                    else:
                        cv2.imwrite(str(frame_path), resized_frame)

                    frame_paths.append(str(frame_path))
                    timestamps.append(timestamp)
                    extracted_count += 1

                frame_count += 1

            logger.info(f"Extracted {extracted_count} frames from {frame_count} total")
            return frame_paths, timestamps

        finally:
            cap.release()

    def extract_frames_from_bytes(
        self,
        video_bytes: bytes,
        video_format: str = "mp4",
        output_dir: Optional[str] = None
    ) -> Tuple[List[str], List[float]]:
        """
        Extract frames from video bytes (for API uploads).

        Args:
            video_bytes: Raw video bytes
            video_format: Video format extension (without dot)
            output_dir: Directory to save extracted frames

        Returns:
            Tuple of (list of frame file paths, list of timestamps in seconds)
        """
        # Write bytes to temporary file
        with tempfile.NamedTemporaryFile(
            suffix=f".{video_format}",
            delete=False
        ) as tmp_file:
            tmp_file.write(video_bytes)
            tmp_path = tmp_file.name

        try:
            return self.extract_frames(tmp_path, output_dir)
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {tmp_path}: {e}")

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize frame to fit within max_dimension while preserving aspect ratio.

        Args:
            frame: Input frame as numpy array

        Returns:
            Resized frame
        """
        height, width = frame.shape[:2]

        # Check if resize is needed
        if max(height, width) <= self.max_dimension:
            return frame

        # Calculate new dimensions
        if width > height:
            new_width = self.max_dimension
            new_height = int(height * self.max_dimension / width)
        else:
            new_height = self.max_dimension
            new_width = int(width * self.max_dimension / height)

        # Resize using high-quality interpolation
        resized = cv2.resize(
            frame,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

        return resized

    def get_video_info(self, video_path: str) -> dict:
        """
        Get information about a video file.

        Args:
            video_path: Path to the video file

        Returns:
            Dictionary with video properties
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {video_path}")

        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0

            return {
                "filename": video_path.name,
                "format": video_path.suffix.lower(),
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "duration_seconds": duration,
                "estimated_extracted_frames": int(duration * self.frames_per_second)
            }

        finally:
            cap.release()

    def cleanup_frames(self, frame_paths: List[str]) -> None:
        """
        Delete extracted frame files.

        Args:
            frame_paths: List of frame file paths to delete
        """
        for path in frame_paths:
            try:
                os.unlink(path)
            except Exception as e:
                logger.warning(f"Failed to delete frame {path}: {e}")

        # Try to remove the parent directory if empty
        if frame_paths:
            parent_dir = Path(frame_paths[0]).parent
            try:
                parent_dir.rmdir()
            except Exception:
                pass  # Directory not empty or other error


# Example usage
if __name__ == "__main__":
    processor = VideoProcessor(
        frames_per_second=1.0,
        max_dimension=1024
    )

    print("VideoProcessor initialized")
    print(f"  Frames per second: {processor.frames_per_second}")
    print(f"  Max dimension: {processor.max_dimension}px")
    print(f"  Output format: {processor.output_format}")
    print(f"\nSupported formats: {', '.join(processor.SUPPORTED_FORMATS)}")
    print("\nExample usage:")
    print("  frame_paths, timestamps = processor.extract_frames('video.mp4')")
    print("  video_info = processor.get_video_info('video.mp4')")
