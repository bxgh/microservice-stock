import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Search, Activity } from 'lucide-react';

const BottomNav: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const tabs = [
        { name: 'Dashboard', path: '/dashboard', icon: Home },
        { name: 'Screener', path: '/screener', icon: Search },
        { name: 'Console', path: '/console', icon: Activity },
    ];

    return (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex justify-around items-center h-16 pb-1 z-50">
            {tabs.map((tab) => {
                const isActive = location.pathname === tab.path;
                const Icon = tab.icon;

                return (
                    <button
                        key={tab.name}
                        onClick={() => navigate(tab.path)}
                        className={`flex flex-col items-center justify-center w-full h-full ${isActive ? 'text-primary' : 'text-gray-400'
                            }`}
                    >
                        <Icon className={`w-6 h-6 mb-1 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                        <span className={`text-xs ${isActive ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
                            {tab.name}
                        </span>
                    </button>
                );
            })}
        </div>
    );
};

export default BottomNav;
