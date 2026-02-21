import React, { useRef, useEffect, useState } from 'react';
import { Link } from 'react-router';
import './topBar.css';
import { ThemeToggle } from "~/modules/theme/components/ThemeToggle";
import { Logo } from '~/modules/shared/components/Logo';

interface TopBarProps {
    isLoggedIn: boolean;
    initials: string;
    onLogin: () => void;
    onLogout: () => void;
}

export function TopBarView({ isLoggedIn, initials, onLogin, onLogout }: TopBarProps) {
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
        <div className="top-bar">
            <div className="top-bar-left">
                <Link to="/" className="logo-link">
                    <Logo size="sm" />
                </Link>
            </div>
            <div className="top-bar-right">
                <ThemeToggle />
                {!isLoggedIn && (
                    <button
                        className="btn btn-primary btn-sm"
                        onClick={onLogin}
                    >
                        Login
                    </button>
                )}

                {isLoggedIn && (
                    <div ref={dropdownRef}>
                        <div
                            className="profile-circle"
                            onClick={() => setShowDropdown(!showDropdown)}
                        >
                            {initials}
                        </div>
                        <div className={`dropdown-menu-custom ${showDropdown ? 'show' : ''}`}>
                            <button className="dropdown-item-custom" onClick={onLogout}>
                                Logout
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
