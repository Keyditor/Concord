/* global React, ReactDOM */
declare var React: any;
declare var ReactDOM: any;
const { useEffect, useState } = React;

const SettingsPage = () => {
	const apiBase = 'http://127.0.0.1:5001';
	const [nickname, setNickname] = useState('New User');
	const [inputDevicePos, setInputDevicePos] = useState('default');
	const [outputDevicePos, setOutputDevicePos] = useState('default');
	const [inputDeviceList, setInputDeviceList] = useState([]); // raw from API
	const [outputDeviceList, setOutputDeviceList] = useState([]); // raw from API
	const [micLevel, setMicLevel] = useState(0);
	const [isChangingDevice, setIsChangingDevice] = useState(false);
	const [micTestOn, setMicTestOn] = useState(false);
	const [inputVolume, setInputVolume] = useState(100);
	const [outputVolume, setOutputVolume] = useState(100);

	useEffect(() => {
		(async () => {
			try { const u = await (await fetch(`${apiBase}/user`)).json(); setNickname(u.username || 'New User'); } catch (e) {}
			try {
				const d = await (await fetch(`${apiBase}/devices`)).json();
				const inList = Array.isArray(d.input) ? d.input : [];
				const outList = Array.isArray(d.output) ? d.output : [];
				setInputDeviceList(inList);
				setOutputDeviceList(outList);
				if (inputDevicePos === 'default' && inList.length) setInputDevicePos('0');
				if (outputDevicePos === 'default' && outList.length) setOutputDevicePos('0');
			} catch (e) {}
			try {
				const v = await (await fetch(`${apiBase}/volume`)).json();
				if (typeof v.input === 'number') setInputVolume(v.input);
				if (typeof v.output === 'number') setOutputVolume(v.output);
			} catch (e) {}
		})();
	}, []);

useEffect(() => {
    if (isChangingDevice || !micTestOn) return;
    const id = setInterval(async () => {
        try {
            const pos = Number(inputDevicePos);
            const idx = Number.isFinite(pos) && inputDeviceList[pos] ? Number(inputDeviceList[pos].index) : undefined;
            const url = Number.isFinite(idx) ? `${apiBase}/mic-level?input=${idx}` : `${apiBase}/mic-level`;
            const r = await fetch(url);
            const d = await r.json();
            if (typeof d.level === 'number') setMicLevel(d.level);
        } catch (e) {}
    }, 500);
    return () => clearInterval(id);
}, [inputDevicePos, inputDeviceList, isChangingDevice, micTestOn]);

	return (
		<div className="min-h-screen text-white p-8">
			<h1 className="text-2xl mb-6">Settings</h1>
			<div className="max-w-xl space-y-8">
				<div>
					<label className="block mb-2">Nickname</label>
					<input value={nickname} onChange={(e) => setNickname(e.target.value)} className="w-full px-3 py-2 bg-gray-700 rounded" />
				</div>
				<div>
			<label className="block mb-2">Input Device</label>
			<select value={inputDevicePos} onFocus={() => { setIsChangingDevice(true); setMicTestOn(false); }} onBlur={() => setIsChangingDevice(false)} onChange={(e) => { setInputDevicePos(e.target.value); }} className="w-full px-3 py-2 bg-gray-700 rounded">
				{inputDeviceList.length === 0 ? (
					<option value={inputDevicePos === 'default' ? 'default' : inputDevicePos}>Default input (system)</option>
				) : inputDeviceList.map((d, idx) => (<option key={`in-${d.index}`} value={String(idx)}>{`${idx}) ${d.name}`}</option>))}
			</select>
				<div className="mt-2 flex items-center gap-3">
					<div className="flex-1 h-2 bg-gray-600 rounded">
						<div className="h-2 bg-green-500 rounded" style={{ width: micTestOn ? `${micLevel}%` : '0%' }}></div>
					</div>
					<button onClick={() => setMicTestOn(v => !v)} className="px-3 py-1 bg-gray-600 rounded">{micTestOn ? 'Stop' : 'Test'}</button>
				</div>
				</div>
				<div>
					<label className="block mb-2">Input Volume</label>
					<div className="flex items-center gap-3">
						<input type="range" min="0" max="100" value={inputVolume} onChange={async (e) => { const val = Number(e.target.value); setInputVolume(val); try { await fetch(`${apiBase}/volume`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ input: val }) }); } catch (err) {} }} className="flex-1" />
						<span className="w-12 text-right">{inputVolume}%</span>
					</div>
				</div>
				<div>
					<label className="block mb-2">Output Device</label>
					<div className="flex items-center gap-3">
			<select value={outputDevicePos} onChange={(e) => setOutputDevicePos(e.target.value)} className="flex-1 px-3 py-2 bg-gray-700 rounded">
				{outputDeviceList.length === 0 ? (
					<option value={outputDevicePos === 'default' ? 'default' : outputDevicePos}>Default output (system)</option>
				) : outputDeviceList.map((d, idx) => (<option key={`out-${d.index}`} value={String(idx)}>{`${idx}) ${d.name}`}</option>))}
			</select>
			<button onClick={async () => { try {
				const pos = Number(outputDevicePos);
				const idx = Number.isFinite(pos) && outputDeviceList[pos] ? Number(outputDeviceList[pos].index) : undefined;
				await fetch(`${apiBase}/test-output`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ output: idx }) });
			} catch (e) {} }} className="px-3 py-2 bg-gray-600 rounded">Test</button>
					</div>
				</div>
				<div>
					<label className="block mb-2">Output Volume</label>
					<div className="flex items-center gap-3">
						<input type="range" min="0" max="100" value={outputVolume} onChange={async (e) => { const val = Number(e.target.value); setOutputVolume(val); try { await fetch(`${apiBase}/volume`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ output: val }) }); } catch (err) {} }} className="flex-1" />
						<span className="w-12 text-right">{outputVolume}%</span>
					</div>
				</div>
				<div className="flex gap-3">
					<a href="/index.html" className="px-4 py-2 bg-gray-600 rounded">Back</a>
			<button onClick={async () => {
				try { await fetch(`${apiBase}/user`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: nickname || 'New User' }) }); } catch (e) {}
				const inIdx = (() => { const pos = Number(inputDevicePos); return Number.isFinite(pos) && inputDeviceList[pos] ? inputDeviceList[pos].index : undefined; })();
				const outIdx = (() => { const pos = Number(outputDevicePos); return Number.isFinite(pos) && outputDeviceList[pos] ? outputDeviceList[pos].index : undefined; })();
				try { await fetch(`${apiBase}/audio-devices`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ input: inIdx, output: outIdx }) }); } catch (e) {}
			}} className="px-4 py-2 bg-blue-600 rounded">Save</button>
				</div>
			</div>
		</div>
	);
};

try {
	const root = ReactDOM.createRoot(document.getElementById('root'));
	root.render(React.createElement(SettingsPage));
} catch (e) {}


