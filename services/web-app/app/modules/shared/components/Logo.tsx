import React from 'react';

interface LogoProps {
    size?: 'sm' | 'lg';
    variant?: 'light' | 'dark' | 'auto';
}

export function Logo({ size = 'sm', variant = 'auto' }: LogoProps) {
    const sizeClasses = size === 'lg'
        ? 'text-4xl md:text-5xl'
        : 'text-xl';

    const variantClasses = variant === 'light'
        ? 'text-linen'
        : variant === 'dark'
            ? 'text-canopy'
            : 'text-canopy';

    return (
        <span className={`${sizeClasses} ${variantClasses} font-sans font-bold tracking-tight select-none`}>
            Carbon<span className="font-light">Bridge</span>
        </span>
    );
}
