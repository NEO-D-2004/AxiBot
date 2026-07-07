import os
import sys

# Ensure project path is added
sys.path.append(os.path.abspath("."))

import riva.client
from app.settings import settings, DEFAULT_NVIDIA_API_KEY

def main():
    print("Testing NVIDIA Riva gRPC TTS call...")
    
    # Use the user's specific Chatterbox key
    api_key = "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"
    
    auth = riva.client.Auth(
        uri="grpc.nvcf.nvidia.com:443",
        use_ssl=True,
        metadata_args=[
            ("function-id", "ddacc747-1269-4fab-bfd9-8f593dead106"),
            ("authorization", f"Bearer {api_key}")
        ]
    )
    
    tts_service = riva.client.SpeechSynthesisService(auth)
    
    try:
        print("Sending synthesis request for text...")
        response = tts_service.synthesize(
            text="Vanakkam makkale! Inime namma stream la join panni enjoy pannunga",
            voice_name="Chatterbox-Multilingual.en-US.Male",
            language_code="ta-IN"
        )
        print("Success! Audio synthesized successfully.")
        print(f"Audio payload size: {len(response.audio)} bytes")
        
        # Save output to scratch directory
        os.makedirs("storage", exist_ok=True)
        wav_path = "storage/test_riva.wav"
        with open(wav_path, "wb") as f:
            f.write(response.audio)
        print(f"Saved audio file to {wav_path}")
    except Exception as e:
        print("gRPC Riva Call failed with exception:")
        print(e)

if __name__ == "__main__":
    main()
