/* global React, ReactDOM */
declare var React: any;
declare var ReactDOM: any;
const { useEffect, useState } = React;

// Minimal placeholder icon components (no external deps)
const Phone = ({ className = '' }) => <span className={className}>📞</span>;
const PhoneOff = ({ className = '' }) => <span className={className}>🛑</span>;
const Settings = ({ className = '' }) => <span className={className}>⚙️</span>;
const User = ({ className = '' }) => <span className={className}>👤</span>;
const Mic = ({ className = '' }) => <span className={className}>🎙️</span>;
const MicOff = ({ className = '' }) => <span className={className}>🔇</span>;
const Volume2 = ({ className = '' }) => <span className={className}>🔊</span>;
const VolumeX = ({ className = '' }) => <span className={className}>🔈</span>;
const ArrowLeft = ({ className = '' }) => <span className={className}>⬅️</span>;
const ChevronDown = ({ className = '' }) => <span className={className}>▾</span>;

const VoiceChatApp = () => {
  const [currentScreen, setCurrentScreen] = useState('main');
  const [activeCall, setActiveCall] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isDeafened, setIsDeafened] = useState(false);
  const [inputVolume, setInputVolume] = useState(75);
  const [outputVolume, setOutputVolume] = useState(80);
  const [nickname, setNickname] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [inputDevice, setInputDevice] = useState('default');
  const [outputDevice, setOutputDevice] = useState('default');
  const [peers, setPeers] = useState([]);
  const apiBase = 'http://127.0.0.1:5001';

  const fetchStatus = async () => {
    try {
      const resp = await fetch(`${apiBase}/status`);
      const data = await resp.json();
      setPeers(data.peers || []);
    } catch (e) {
      // ignore
    }
  };

  const fetchVolume = async () => {
    try {
      const resp = await fetch(`${apiBase}/volume`);
      const data = await resp.json();
      if (typeof data.input === 'number') setInputVolume(data.input);
      if (typeof data.output === 'number') setOutputVolume(data.output);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    // Initial loads
    fetchStatus();
    fetchVolume();
    // Load user and available devices once
    (async () => {
      try {
        const u = await (await fetch(`${apiBase}/user`)).json();
        setNickname(u.username || 'New User');
      } catch (e) { setNickname('New User'); }
      try {
        const d = await (await fetch(`${apiBase}/devices`)).json();
        // store available devices (simple: take first as default selections if 'default')
        if (inputDevice === 'default' && Array.isArray(d.input) && d.input.length) {
          setInputDevice(String(d.input[0].index ?? 'default'));
        }
        if (outputDevice === 'default' && Array.isArray(d.output) && d.output.length) {
          setOutputDevice(String(d.output[0].index ?? 'default'));
        }
      } catch (e) {}
    })();
    // Poll only peers every 5s
    const id = setInterval(fetchStatus, 5000);
    return () => clearInterval(id);
  }, []);

  // Mock audio devices - em um app real, você obteria isso via navigator.mediaDevices.enumerateDevices()
  const audioInputDevices = [
    { id: 'default', label: 'Default Microphone' },
    { id: 'mic1', label: 'USB Microphone (Blue Yeti)' },
    { id: 'mic2', label: 'Headset Microphone' },
    { id: 'mic3', label: 'Built-in Microphone' }
  ];

  const audioOutputDevices = [
    { id: 'default', label: 'Default Speaker' },
    { id: 'speaker1', label: 'Speakers (Realtek Audio)' },
    { id: 'headphone1', label: 'Headphones (Sony WH-1000XM4)' },
    { id: 'headphone2', label: 'USB Headset' }
  ];

  const handleCallIp = async (ip, control_port) => {
    try {
      const resp = await fetch(`${apiBase}/call`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ ip, control_port }) });
      if (resp.ok) {
        setActiveCall(ip);
      }
    } catch (e) {}
  };

  const handleCall = (peer) => {
    handleCallIp(peer.ip, peer.control_port);
  };

  const handleEndCall = async () => {
    try { await fetch(`${apiBase}/hangup`, { method: 'POST' }); } catch (e) {}
    setActiveCall(null);
  };

  const MainScreen = () => (
    <div className="flex h-full">
      {/* Left Panel - Peers */}
      <div className="w-1/2 p-6 border-r border-gray-600">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-light text-white">Peers</h2>
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="p-2 rounded-lg bg-gray-600 hover:bg-gray-500 transition-colors"
            >
              <ChevronDown className="w-5 h-5 text-white" />
            </button>
            {showDropdown && (
              <div className="absolute right-0 top-full mt-2 bg-gray-700 rounded-lg shadow-lg z-10 min-w-[120px]">
                <button
                  onClick={() => {
                    setCurrentScreen('settings');
                    setShowDropdown(false);
                  }}
                  className="w-full px-4 py-2 text-left text-white hover:bg-gray-600 rounded-lg flex items-center gap-2"
                >
                  <Settings className="w-4 h-4" />
                  Settings
                </button>
              </div>
            )}
          </div>
        </div>
        
        <div className="space-y-4">
          {peers.map((peer) => (
            <div key={peer.ip} className="flex items-center justify-between p-4 rounded-xl bg-gray-700/50 hover:bg-gray-700 transition-colors">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-full ${peer.color} flex items-center justify-center relative`}>
                  <User className="w-6 h-6 text-white" />
                  {peer.online && (
                    <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-gray-800"></div>
                  )}
                </div>
                <span className="text-white font-medium">{peer.username || peer.ip}</span>
              </div>
              <button
                onClick={() => handleCall(peer)}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
              >
                Call
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-1/2 p-6 flex flex-col">
        {/* Active Calls */}
        <div className="mb-8">
          <h2 className="text-2xl font-light text-white mb-6">Active Calls</h2>
          {activeCall ? (
            <div className="p-6 rounded-xl bg-gray-700/50 border border-gray-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                <span className="text-xl text-white font-medium">{activeCall || ''}</span>
                </div>
                <button
                  onClick={handleEndCall}
                  className="p-3 bg-red-600 hover:bg-red-700 rounded-full transition-colors"
                >
                  <PhoneOff className="w-6 h-6 text-white" />
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-xl bg-gray-700/20 border-2 border-dashed border-gray-600 text-center">
              <Phone className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-400">No active calls</p>
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="mt-auto">
          <div className="flex justify-center gap-4 mb-6">
            <button
              onClick={() => setIsMuted(!isMuted)}
              className={`p-4 rounded-full transition-colors ${
                isMuted ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-600 hover:bg-gray-500'
              }`}
            >
              {isMuted ? <MicOff className="w-6 h-6 text-white" /> : <Mic className="w-6 h-6 text-white" />}
            </button>
            <button
              onClick={() => setIsDeafened(!isDeafened)}
              className={`p-4 rounded-full transition-colors ${
                isDeafened ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-600 hover:bg-gray-500'
              }`}
            >
              {isDeafened ? <VolumeX className="w-6 h-6 text-white" /> : <Volume2 className="w-6 h-6 text-white" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const SettingsScreen = () => (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => setCurrentScreen('main')}
          className="p-2 rounded-lg bg-gray-600 hover:bg-gray-500 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-white" />
        </button>
        <h1 className="text-3xl font-light text-white">Settings</h1>
      </div>

      <div className="space-y-8">
        {/* Audio Settings */}
        <div className="bg-gray-700/30 rounded-xl p-6">
          <h3 className="text-xl text-white mb-6 flex items-center gap-3">
            <Volume2 className="w-5 h-5" />
            Audio Settings
          </h3>
          
          <div className="space-y-6">
            {/* Input Device Selection */}
            <div>
              <label className="block text-gray-300 mb-3 font-medium">Input Device</label>
              <select
                value={inputDevice}
                onChange={(e) => setInputDevice(e.target.value)}
                className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg border border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              >
                {/* populated from backend via /devices on mount; keep simple default for now */}
                <option value={inputDevice} className="bg-gray-600">{inputDevice}</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-300 mb-3 font-medium">Input volume</label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={inputVolume}
                  onChange={async (e) => {
                    const val = Number(e.target.value);
                    setInputVolume(val);
                    try { await fetch(`${apiBase}/volume`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ input: val }) }); } catch (err) {}
                  }}
                  className="flex-1 h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
                />
                <span className="text-white font-mono w-12 text-right">{inputVolume}%</span>
              </div>
            </div>

            {/* Output Device Selection */}
            <div>
              <label className="block text-gray-300 mb-3 font-medium">Output Device</label>
              <select
                value={outputDevice}
                onChange={(e) => setOutputDevice(e.target.value)}
                className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg border border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              >
                <option value={outputDevice} className="bg-gray-600">{outputDevice}</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-300 mb-3 font-medium">Output volume</label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={outputVolume}
                  onChange={async (e) => {
                    const val = Number(e.target.value);
                    setOutputVolume(val);
                    try { await fetch(`${apiBase}/volume`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ output: val }) }); } catch (err) {}
                  }}
                  className="flex-1 h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
                />
                <span className="text-white font-mono w-12 text-right">{outputVolume}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Profile Settings */}
        <div className="bg-gray-700/30 rounded-xl p-6">
          <h3 className="text-xl text-white mb-6 flex items-center gap-3">
            <User className="w-5 h-5" />
            Profile Settings
          </h3>
          
          <div>
            <label className="block text-gray-300 mb-3 font-medium">Nickname</label>
            <input
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              placeholder="Enter your nickname"
              className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg border border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={async () => {
              try { await fetch(`${apiBase}/user`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: nickname || 'New User' }) }); } catch (e) {}
              try { await fetch(`${apiBase}/audio-devices`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ input: inputDevice, output: outputDevice }) }); } catch (e) {}
              setCurrentScreen('main');
            }}
            className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Save Changes
          </button>
          <button
            onClick={() => setCurrentScreen('main')}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-500 text-white rounded-lg font-medium transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="w-full h-screen bg-gray-800 flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 px-6 py-4 flex items-center justify-between border-b border-gray-700">
        <h1 className="text-2xl font-light text-white tracking-wider">CONCORD</h1>
        <div className="flex gap-2">
          <button className="w-6 h-6 bg-yellow-500 rounded hover:bg-yellow-600 transition-colors"></button>
          <button className="w-6 h-6 bg-gray-600 border border-gray-500 hover:bg-gray-500 transition-colors"></button>
          <button className="w-6 h-6 bg-red-500 rounded hover:bg-red-600 transition-colors"></button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {currentScreen === 'main' ? <MainScreen /> : <SettingsScreen />}
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: 2px solid #1f2937;
        }
        
        .slider::-moz-range-thumb {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: 2px solid #1f2937;
        }
      `}</style>
    </div>
  );
};

// export removed for browser usage

// Mount in browser if available
try {
  const rootEl = document.getElementById('root');
  if (rootEl && ReactDOM && ReactDOM.createRoot) {
    const root = ReactDOM.createRoot(rootEl);
    root.render(React.createElement(VoiceChatApp));
  }
} catch (e) {}