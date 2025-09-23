/* global React, ReactDOM */
declare var React: any;
declare var ReactDOM: any;
const { useEffect, useState } = React;

const SettingsPage = () => {
	const apiBase = 'http://127.0.0.1:5001';
	const [nickname, setNickname] = useState('New User');
	const [inputDevice, setInputDevice] = useState('default');
	const [outputDevice, setOutputDevice] = useState('default');
	const [inputDeviceList, setInputDeviceList] = useState([]);
	const [outputDeviceList, setOutputDeviceList] = useState([]);

	useEffect(() => {
		(async () => {
			try { const u = await (await fetch(`${apiBase}/user`)).json(); setNickname(u.username || 'New User'); } catch (e) {}
			try {
				const d = await (await fetch(`${apiBase}/devices`)).json();
				const inList = Array.isArray(d.input) ? d.input : [];
				const outList = Array.isArray(d.output) ? d.output : [];
				setInputDeviceList(inList);
				setOutputDeviceList(outList);
				if (inputDevice === 'default' && inList.length) setInputDevice(String(inList[0].index));
				if (outputDevice === 'default' && outList.length) setOutputDevice(String(outList[0].index));
			} catch (e) {}
		})();
	}, []);

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
					<select value={inputDevice} onChange={(e) => setInputDevice(e.target.value)} className="w-full px-3 py-2 bg-gray-700 rounded">
						{inputDeviceList.map((d) => (<option key={`in-${d.index}`} value={String(d.index)}>{d.name}</option>))}
					</select>
				</div>
				<div>
					<label className="block mb-2">Output Device</label>
					<select value={outputDevice} onChange={(e) => setOutputDevice(e.target.value)} className="w-full px-3 py-2 bg-gray-700 rounded">
						{outputDeviceList.map((d) => (<option key={`out-${d.index}`} value={String(d.index)}>{d.name}</option>))}
					</select>
				</div>
				<div className="flex gap-3">
					<a href="/index.html" className="px-4 py-2 bg-gray-600 rounded">Back</a>
					<button onClick={async () => {
						try { await fetch(`${apiBase}/user`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ username: nickname || 'New User' }) }); } catch (e) {}
						try { await fetch(`${apiBase}/audio-devices`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ input: Number(inputDevice), output: Number(outputDevice) }) }); } catch (e) {}
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


