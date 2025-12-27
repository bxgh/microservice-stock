import React, { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Search, BarChart2, Cpu } from 'lucide-react';

const BottomNav: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const tabs = useMemo(() => [
        { name: '首页', path: '/dashboard', icon: Home },
        { name: '选股', path: '/screener', icon: Search },
        { name: '行情', path: '/stock/sh600519', icon: BarChart2 }, // Default to a major stock
        { name: '管理', path: '/console', icon: Cpu },
    ], []);

    // Calculate active index for the sliding indicator
    const activeIndex = tabs.findIndex(tab => {
        if (tab.path.startsWith('/stock/')) {
            return location.pathname.startsWith('/stock/');
        }
        return location.pathname === tab.path;
    });

    const indicatorStyle = {
        width: `calc(calc(100% - 24px) / ${tabs.length})`,
        left: activeIndex === -1
            ? '0px'
            : `calc(12px + (calc(calc(100% - 24px) / ${tabs.length}) * ${activeIndex}))`,
        opacity: activeIndex === -1 ? 0 : 1
    };

    return (
        <nav className="floating-island-nav">
            {/* Sliding Island Indicator */}
            <div className="nav-indicator" style={indicatorStyle} />

            {tabs.map((tab) => {
                const isActive = tab.path.startsWith('/stock/')
                    ? location.pathname.startsWith('/stock/')
                    : location.pathname === tab.path;
                const Icon = tab.icon;

                return (
                    <button
                        key={tab.name}
                        onClick={() => navigate(tab.path)}
                        className={`nav-item ${isActive ? 'active' : ''}`}
                    >
                        <Icon className={`w-5 h-5 transition-transform duration-300 ${isActive ? 'scale-110 mb-0.5' : 'mb-0.5'}`} />
                        <span className="text-[10px] font-bold tracking-tight">{tab.name}</span>
                    </button>
                );
            })}
        </nav>
    );
};

export default BottomNav;
