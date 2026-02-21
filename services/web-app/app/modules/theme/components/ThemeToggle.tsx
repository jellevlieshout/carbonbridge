import React, { useRef, useEffect, useState } from 'react';
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import "~/modules/layout/components/TopBar/topBar.css"; // Ensure styles are available

export function ThemeToggle() {
    const { setTheme } = useTheme()
    const [showDropdown, setShowDropdown] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setShowDropdown(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    return (
        <div ref={dropdownRef} className="relative inline-block text-left mr-4">
            <button
                className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center justify-center border border-gray-200 dark:border-gray-700 mr-2"
                onClick={() => setShowDropdown(!showDropdown)}
                aria-label="Toggle theme"
            >
                <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0 text-foreground" />
                <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100 text-foreground" />
            </button>

            <div className={`dropdown-menu-custom ${showDropdown ? 'show' : ''}`} style={{ width: 'auto', minWidth: '100px', right: 0 }}>
                <button className="dropdown-item-custom" onClick={() => { setTheme("light"); setShowDropdown(false); }}>
                    Light
                </button>
                <button className="dropdown-item-custom" onClick={() => { setTheme("dark"); setShowDropdown(false); }}>
                    Dark
                </button>
                <button className="dropdown-item-custom" onClick={() => { setTheme("system"); setShowDropdown(false); }}>
                    System
                </button>
            </div>
        </div>
    )
}
