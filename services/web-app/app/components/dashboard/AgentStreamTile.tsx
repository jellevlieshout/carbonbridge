import React, { useEffect, useState } from 'react';

type StreamLog = {
    id: number;
    time: string;
    tag: 'SCAN' | 'ALERT' | 'MATCH' | 'HOLD';
    text: string;
};

const initialLogs: StreamLog[] = [
    { id: 1, time: '14:20:01', tag: 'SCAN', text: 'Initiating registry deep-scan...' },
    { id: 2, time: '14:21:15', tag: 'HOLD', text: 'Market volume low. Bids paused.' },
];

const newLogsPool = [
    { tag: 'ALERT', text: 'New vintage 2023 WCC credits detected at €12.50' },
    { tag: 'SCAN', text: 'Cross-referencing CarbonPlan OffsetsDB ratings...' },
    { tag: 'MATCH', text: 'Found 140t matching criteria. Simulating purchase.' },
    { tag: 'HOLD', text: 'Price ceiling exceeded by €0.40. Cancelling sim.' },
    { tag: 'SCAN', text: 'Awaiting next market tick.' },
];

export function AgentStreamTile() {
    const [logs, setLogs] = useState<StreamLog[]>(initialLogs);

    useEffect(() => {
        let count = 0;
        const interval = setInterval(() => {
            if (count >= newLogsPool.length) return;

            const newLogItem = newLogsPool[count];
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            const newLog: StreamLog = {
                id: Date.now(),
                time: timeStr,
                tag: newLogItem.tag as any,
                text: newLogItem.text
            };

            setLogs(prev => [newLog, ...prev]);
            count++;
        }, 4000);

        return () => clearInterval(interval);
    }, []);

    const getTagColor = (tag: string) => {
        switch (tag) {
            case 'SCAN': return 'text-slate/60 bg-slate/10';
            case 'ALERT': return 'text-amber-700 bg-amber-100';
            case 'MATCH': return 'text-emerald-700 bg-emerald-100';
            case 'HOLD': return 'text-ember bg-ember/10';
            default: return 'text-slate bg-slate/10';
        }
    };

    return (
        <div className="flex flex-col h-full w-full rounded-[1.25rem] bg-slate text-linen p-6 shadow-sm overflow-hidden relative">
            {/* Noise Texture */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.05] mix-blend-overlay z-0"
                style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }}
            />

            <div className="flex items-center justify-between mb-4 relative z-10 border-b border-linen/10 pb-4">
                <h3 className="font-sans font-semibold tracking-tight">Agent Stream</h3>
                <div className="flex items-center gap-2 bg-ember/20 px-2 py-1 rounded-[1rem] border border-ember/30">
                    <div className="w-1.5 h-1.5 rounded-full bg-ember animate-ping" />
                    <span className="font-mono text-[10px] uppercase font-semibold text-ember tracking-wider">Watching</span>
                </div>
            </div>

            <div className="relative z-10 flex-1 overflow-hidden flex flex-col justify-start mask-image-bottom">
                <div className="flex flex-col gap-3">
                    {logs.map((log, i) => (
                        <div
                            key={log.id}
                            className="flex flex-col text-sm font-mono animate-in slide-in-from-top-2 fade-in duration-500 ease-out"
                            style={{ opacity: Math.max(0.2, 1 - (i * 0.25)) }}
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] text-linen/40">{log.time}</span>
                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-[4px] uppercase ${getTagColor(log.tag)}`}>
                                    {log.tag}
                                </span>
                            </div>
                            <p className="text-xs leading-relaxed text-linen/80">{log.text}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
