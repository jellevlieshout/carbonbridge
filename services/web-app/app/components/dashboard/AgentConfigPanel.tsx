import React, { useState } from 'react';


export function AgentConfigPanel() {
    const [budget, setBudget] = useState("2400");
    const [enabled, setEnabled] = useState(true);
    const [preferences, setPreferences] = useState(['forestry', 'soil']);
    const [vintage, setVintage] = useState([2021]);

    const togglePreference = (val: string) => {
        setPreferences(prev => prev.includes(val) ? prev.filter(p => p !== val) : [...prev, val]);
    };

    const getPrefLabels = () => {
        if (preferences.length === 0) return "any project type";
        return preferences.map(p => {
            if (p === 'forestry') return 'forestry';
            if (p === 'soil') return 'soil carbon';
            if (p === 'cookstoves') return 'cookstoves';
            if (p === 'renewables') return 'renewables';
            return '';
        }).join(' and ');
    };

    return (
        <div className="w-full mt-12 bg-mist rounded-[2rem] border-l-[8px] border-l-canopy overflow-hidden shadow-sm flex flex-col transition-colors duration-500">
            <div className="p-10 flex flex-col lg:flex-row gap-12 justify-between">

                {/* Settings Form */}
                <div className="flex-1 flex flex-col gap-10">
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <label className="font-sans font-semibold text-slate text-lg">Budget Ceiling</label>
                        </div>
                        <div className="relative w-fit">
                            <span className="absolute left-4 top-1/2 -translate-y-1/2 font-mono text-slate/50">£</span>
                            <input
                                type="number"
                                value={budget}
                                onChange={(e) => setBudget(e.target.value)}
                                className="h-14 bg-white border border-slate/10 rounded-xl pl-10 pr-6 w-48 font-mono text-lg text-slate outline-none focus:border-ember transition-colors"
                            />
                            <span className="font-mono text-sm text-slate/50 ml-4">Agent may spend up to £{budget || "0"} / quarter</span>
                        </div>
                    </div>

                    <div>
                        <label className="font-sans font-semibold text-slate text-lg mb-4 block">Credit Type Preference</label>
                        <div className="flex flex-wrap gap-3">
                            {['forestry', 'soil', 'cookstoves', 'renewables'].map(type => {
                                const isSelected = preferences.includes(type);
                                return (
                                    <button
                                        key={type}
                                        onClick={() => togglePreference(type)}
                                        className={`px-5 py-3 rounded-full font-medium transition-all duration-300 ${isSelected ? 'bg-sage text-linen shadow-sm' : 'bg-white text-slate/60 hover:text-slate'}`}
                                    >
                                        {type.charAt(0).toUpperCase() + type.slice(1).replace('-', ' ')}
                                    </button>
                                )
                            })}
                        </div>
                    </div>

                    <div className="w-full max-w-md">
                        <div className="flex justify-between items-center mb-4">
                            <label className="font-sans font-semibold text-slate text-lg">Vintage Floor</label>
                            <span className="font-mono text-slate/70">{vintage} onwards</span>
                        </div>
                        <input
                            type="range"
                            min={2018}
                            max={2024}
                            step={1}
                            value={vintage[0]}
                            onChange={(e) => setVintage([parseInt(e.target.value)])}
                            className="w-full accent-ember mt-4"
                        />
                    </div>
                </div>

                {/* Status Toggle & Summary */}
                <div className="lg:w-1/3 flex flex-col items-start lg:items-end justify-between bg-white/50 p-8 rounded-2xl border border-white/60">
                    <div className="flex items-center gap-4 w-full justify-between">
                        <span className="font-sans font-bold text-xl text-slate">{enabled ? "Agent Enabled" : "Agent Paused"}</span>
                        <button
                            onClick={() => setEnabled(!enabled)}
                            className={`w-12 h-6 rounded-full transition-colors relative flex items-center ${enabled ? 'bg-ember' : 'bg-slate/20'}`}
                        >
                            <span className={`w-4 h-4 rounded-full bg-white absolute transition-transform ${enabled ? 'translate-x-7' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    <div className={`mt-12 transition-opacity duration-500 ${enabled ? 'opacity-100' : 'opacity-40'}`}>
                        <p className="font-serif italic text-2xl text-canopy leading-snug">
                            "Your agent will autonomously purchase verified {getPrefLabels()} credits from {vintage} onwards, up to £{budget || '0'} per quarter, without further approval."
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
