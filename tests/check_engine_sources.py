"""Check the pinned public API and generated project; no Apple SDK compilation."""
import re
import subprocess
import sys
from pathlib import Path
base = Path(__file__).resolve().parents[1]
engine = Path(sys.argv[1]).resolve()
subprocess.run([sys.executable, str(base/'generate_project.py'), str(engine)], check=True)
text = (base/'DexAetherBridge.xcodeproj/project.pbxproj').read_text()
ids = re.findall(r'^\s+([A-F0-9]{24}) =', text, re.M)
assert len(ids) == len(set(ids))
assert set(re.findall(r'\b[A-F0-9]{24}\b', text)) == set(ids)
assert 'productName = AetherEngine;' in text and 'EXPORTED_SYMBOLS_FILE' in text
state = (engine/'Sources/AetherEngine/PlayerState.swift').read_text()
for name in ('objectAudioRendering', 'confirmAtmos', 'externalSubtitles', 'autoplay'):
    assert 'public var ' + name in state
assert 'TrackInfo: Identifiable, Sendable, Equatable' in state
object_audio = (engine/'Sources/AetherEngine/Audio/Spatial/ObjectAudioRendering.swift').read_text()
assert 'case apac(SpatialSpeakerLayout)' in object_audio
bridge = (base/'DexAetherEmbedded.swift').read_text()
for selector in ('@objc(startEmbedded:inView:belowView:)', '@objc(snapshotForToken:)', '@objc(command:)'):
    assert selector in bridge
assert 'MainActor.assumeIsolated' in bridge and 'confirmAtmos: true' in bridge
assert 'lastAudio != engine.audioTracks' in bridge
assert not (base/'engines').exists()
print('PASS: pinned Aether API, project references and bridge contract. Apple SDK type checking remains pending.')
