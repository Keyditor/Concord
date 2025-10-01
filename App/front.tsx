/* eslint-disable no-redeclare */
/* global React, ReactDOM */
declare var React: any;
declare var ReactDOM: any;

// Minimal placeholder icon components (no external deps)
const Phone = ({ className = '' }) => <span className={className}>📞</span>;
const PhoneOff = ({ className = '' }) => <span className={className}>🛑</span>;
const Settings = ({ className = '' }) => <span className={className}>⚙️</span>;
const User = ({ className = '' }) => <span className={className}>👤</span>;
const Mic = ({ className = '' }) => <span className={className}>🎙️</span>;
const MicOff = ({ className = '' }) => <span className={className}>🎙️</span>;
const Volume2 = ({ className = '' }) => <span className={className}>🔊</span>;
const VolumeX = ({ className = '' }) => <span className={className}>🔈</span>;
const ArrowLeft = ({ className = '' }) => <span className={className}>⬅️</span>;
const ChevronDown = ({ className = '' }) => <span className={className}>▾</span>;

const VoiceChatApp = () => {
  const { useEffect, useState } = React;
  const [currentScreen, setCurrentScreen] = React.useState('main');
  const [activeCall, setActiveCall] = React.useState(null);
  const [isMuted, setIsMuted] = React.useState(false);
  const [isDeafened, setIsDeafened] = React.useState(false);
  const [inputVolume, setInputVolume] = React.useState(75);
  const [outputVolume, setOutputVolume] = React.useState(80);
  const [nickname, setNickname] = React.useState('');
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [inputDevicePos, setInputDevicePos] = React.useState('default');
  const [outputDevicePos, setOutputDevicePos] = React.useState('default');
  const [inputDeviceList, setInputDeviceList] = React.useState([]); // raw from API
  const [outputDeviceList, setOutputDeviceList] = React.useState([]); // raw from API
  const [peers, setPeers] = React.useState([]);
  const [pendingOffer, setPendingOffer] = React.useState(null);
  const [localInterfaces, setLocalInterfaces] = React.useState([]);
  const [selectedNetwork, setSelectedNetwork] = React.useState('all');
  const apiBase = 'http://127.0.0.1:5001';

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
    fetchVolume();
    (async () => {
      try {
        const u = await (await fetch(`${apiBase}/user`)).json();
        setNickname(u.username || 'New User');
      } catch (e) { setNickname('New User'); }
      try {
        const d = await (await fetch(`${apiBase}/devices`)).json();
        const inList = Array.isArray(d.input) ? d.input : [];
        const outList = Array.isArray(d.output) ? d.output : [];
        setInputDeviceList(inList);
        setOutputDeviceList(outList);
        if (inputDevicePos === 'default' && inList.length) {
          setInputDevicePos('0');
        }
        if (outputDevicePos === 'default' && outList.length) {
          setOutputDevicePos('0');
        }
      } catch (e) {}
    })();
  }, []);

  // Subscribe to real-time events for peers and status
  useEffect(() => {
    if (currentScreen !== 'main') return;

    // Subscribe to peer updates
    let peer_es;
    const peerUrl = selectedNetwork === 'all' ? `${apiBase}/events/peers` : `${apiBase}/events/peers?network=${encodeURIComponent(selectedNetwork)}`;
    try {
      peer_es = new EventSource(peerUrl);
      peer_es.onmessage = (ev) => {
        try { const list = JSON.parse(ev.data); if (Array.isArray(list)) { setPeers(list); } } catch (e) {}
      };
    } catch (e) {}

    // Subscribe to status updates (calls, pending offers)
    let status_es;
    try {
      status_es = new EventSource(`${apiBase}/events/status`);
      status_es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (Array.isArray(data.interfaces)) setLocalInterfaces(data.interfaces);
          setPendingOffer(data.pending_offer || null);
          setActiveCall(data.in_call ? data.current_call : null);
        } catch (e) {}
      };
    } catch (e) {}

    // Cleanup function to close connections when component unmounts or screen changes
    return () => { try { peer_es && peer_es.close(); status_es && status_es.close(); } catch (e) {} };
  }, [currentScreen, selectedNetwork]);

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
        const data = await resp.json();
        // setActiveCall(data); // No longer needed, status event will handle it
      }
    } catch (e) {}
  };

  const handleCall = (peer) => {
    handleCallIp(peer.ip, peer.control_port);
  };

  const handleEndCall = async () => {
    try { await fetch(`${apiBase}/hangup`, { method: 'POST' }); } catch (e) {}
    // setActiveCall(null); // No longer needed, status event will handle it
  };

  const MainScreen = () => (
    <div className="flex h-full">
      {/* Left Panel - Peers */}
      <div className="w-1/2 p-6 border-r border-gray-600">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-light text-white">Peers</h2>
            {localInterfaces.length > 0 && (
              <div className="flex items-center gap-2">
                <select
                  value={selectedNetwork}
                  onChange={(e) => setSelectedNetwork(e.target.value)}
                  className="bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
                >
                  <option value="all">All Networks</option>
                  {localInterfaces.map(iface => (
                    <option key={iface.network} value={iface.network}>{iface.network}</option>
                  ))}
                </select>
                <button onClick={async () => { try { await fetch(`${apiBase}/peers/discover`, { method: 'POST' }); } catch (e) {} }} className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors">
                  Buscar
                </button>
              </div>
            )}
          </div>
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="p-2 rounded-lg bg-gray-600 hover:bg-gray-500 transition-colors"
            >
              <ChevronDown className="w-5 h-5 text-white" />
            </button>
            {showDropdown && (
              <div className="absolute right-0 top-full mt-2 bg-gray-700 rounded-lg shadow-lg z-10 min-w-[120px]">
                <a href="/settings.html" onClick={() => { try { fetch(`${apiBase}/ui-state`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: 'settings' }) }); } catch (e) {} }} className="w-full block px-4 py-2 text-left text-white hover:bg-gray-600 rounded-lg flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Settings
                </a>
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
          {pendingOffer && !activeCall ? (
            <div className="p-6 rounded-xl bg-gray-700/50 border border-yellow-600 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-yellow-500 flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-xl text-white font-medium">Incoming: {pendingOffer.peer_username || pendingOffer.peer_ip}</span>
                </div>
                <div className="flex gap-3">
                  <button onClick={async () => { try { await fetch(`${apiBase}/accept`, { method: 'POST' }); } catch (e) {} }} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white">Accept</button>
                  <button onClick={async () => { try { await fetch(`${apiBase}/reject`, { method: 'POST' }); } catch (e) {} setPendingOffer(null); }} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-white">Reject</button>
                </div>
              </div>
            </div>
          ) : null}
          {activeCall ? (
            <div className="p-6 rounded-xl bg-gray-700/50 border border-gray-600">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                <span className="text-xl text-white font-medium">{typeof activeCall === 'object' ? (activeCall.remote_username || activeCall.remote_ip) : String(activeCall)}</span>
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
                value={inputDevicePos}
                onChange={(e) => setInputDevicePos(e.target.value)}
                className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg border border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              >
                {inputDeviceList.length === 0 && (
                  <option value={inputDevicePos === 'default' ? 'default' : inputDevicePos} className="bg-gray-600">Default input (system)</option>
                )}
                {inputDeviceList.map((d, idx) => (
                  <option key={`in-${d.index}`} value={String(idx)} className="bg-gray-600">{`${idx}) ${d.name}`}</option>
                ))}
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
                value={outputDevicePos}
                onChange={(e) => setOutputDevicePos(e.target.value)}
                className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg border border-gray-500 focus:border-blue-500 focus:outline-none transition-colors"
              >
                {outputDeviceList.length === 0 && (
                  <option value={outputDevicePos === 'default' ? 'default' : outputDevicePos} className="bg-gray-600">Default output (system)</option>
                )}
                {outputDeviceList.map((d, idx) => (
                  <option key={`out-${d.index}`} value={String(idx)} className="bg-gray-600">{`${idx}) ${d.name}`}</option>
                ))}
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
              const inIdx = (() => { const pos = Number(inputDevicePos); return Number.isFinite(pos) && inputDeviceList[pos] ? inputDeviceList[pos].index : undefined; })();
              const outIdx = (() => { const pos = Number(outputDevicePos); return Number.isFinite(pos) && outputDeviceList[pos] ? outputDeviceList[pos].index : undefined; })();
              try { await fetch(`${apiBase}/audio-devices`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ input: inIdx, output: outIdx }) }); } catch (e) {}
              try { await fetch(`${apiBase}/ui-state`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: 'main' }) }); } catch (e) {}
              setCurrentScreen('main');
            }}
            className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Save Changes
          </button>
          <button
            onClick={async () => { try { await fetch(`${apiBase}/ui-state`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: 'main' }) }); } catch (e) {} setCurrentScreen('main'); }}
            className="px-6 py-3 bg-gray-600 hover:bg-gray-500 text-white rounded-lg font-medium transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );

  return (
      <div className="w-full h-screen bg-gray-800 flex flex-col" style={{ WebkitAppRegion: 'no-drag' }}>
      {/* Header (sem a barra customizada, pois a nativa foi reativada) */}
      <div className="bg-gray-900 px-6 py-4 flex items-center justify-center border-b border-gray-700 select-none">
        <h1 className="text-xl font-light text-white tracking-wider" style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' }}>Spea-K</h1>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden" style={{ WebkitAppRegion: 'no-drag' }}>
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