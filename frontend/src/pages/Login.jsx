import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, LogIn, User, Lock, ArrowRight } from 'lucide-react';
import NeoButton from '../components/NeoButton';

export default function Login() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        // No backend — just navigate forward
        navigate('/');
    };

    return (
        <div className="min-h-screen bg-neo-cream flex flex-col items-center justify-center relative overflow-hidden px-4">
            {/* Background decorations */}
            <div className="absolute inset-0 opacity-20 pointer-events-none">
                <div className="absolute top-20 left-10 w-32 h-32 border-[4px] border-neo-navy rotate-12"></div>
                <div className="absolute top-40 right-20 w-24 h-24 border-[4px] border-neo-teal -rotate-6"></div>
                <div className="absolute bottom-20 left-1/4 w-16 h-16 bg-neo-orange"></div>
                <div className="absolute bottom-40 right-1/3 w-20 h-20 bg-neo-teal rotate-45"></div>
                <div className="absolute top-1/3 right-10 w-12 h-12 border-[4px] border-neo-orange rotate-45"></div>
                <div className="absolute bottom-1/4 left-16 w-28 h-28 border-[4px] border-neo-maroon -rotate-12"></div>
            </div>

            {/* Logo */}
            <div className="relative z-10 mb-8 text-center">
                <h1 className="text-6xl md:text-8xl font-heading font-bold leading-none text-neo-navy">
                    TRADE
                    <span className="block text-neo-orange relative">
                        MIND
                        <svg className="absolute -bottom-2 left-0 w-full h-4" viewBox="0 0 200 20">
                            <path d="M0 10 Q50 0, 100 10 T200 10" stroke="#FF7D00" strokeWidth="4" fill="none" />
                        </svg>
                    </span>
                </h1>
            </div>

            {/* Login Card */}
            <div className="relative z-10 w-full max-w-md neo-card p-8">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-neo-teal border-[3px] border-neo-navy flex items-center justify-center">
                        <LogIn className="w-5 h-5 text-neo-cream" />
                    </div>
                    <h2 className="text-2xl font-heading font-bold text-neo-navy">SIGN IN</h2>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Username */}
                    <div>
                        <label className="block text-xs font-heading font-bold text-neo-navy/60 uppercase tracking-widest mb-2">
                            Username
                        </label>
                        <div className="flex items-center border-[3px] border-neo-navy overflow-hidden">
                            <span className="px-3 py-3 bg-neo-navy text-neo-cream">
                                <User className="w-5 h-5" />
                            </span>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter your username"
                                className="flex-1 px-4 py-3 bg-neo-cream text-neo-navy font-body placeholder:text-neo-navy/40 focus:outline-none focus:bg-white transition-colors"
                            />
                        </div>
                    </div>

                    {/* Password */}
                    <div>
                        <label className="block text-xs font-heading font-bold text-neo-navy/60 uppercase tracking-widest mb-2">
                            Password
                        </label>
                        <div className="flex items-center border-[3px] border-neo-navy overflow-hidden">
                            <span className="px-3 py-3 bg-neo-navy text-neo-cream">
                                <Lock className="w-5 h-5" />
                            </span>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                className="flex-1 px-4 py-3 bg-neo-cream text-neo-navy font-body placeholder:text-neo-navy/40 focus:outline-none focus:bg-white transition-colors"
                            />
                        </div>
                    </div>

                    {/* Submit Button */}
                    <NeoButton
                        type="submit"
                        variant="orange"
                        size="lg"
                        className="w-full mt-2"
                    >
                        <span className="flex items-center justify-center gap-2">
                            Continue
                            <ArrowRight className="w-5 h-5" />
                        </span>
                    </NeoButton>
                </form>


            </div>

            {/* Bottom tag */}
            <div className="relative z-10 mt-6">
                <span className="neo-badge-navy text-xs">
                    <TrendingUp className="w-3 h-3" />
                    NEGOTIATION AI ENGINE v1.0
                </span>
            </div>
        </div>
    );
}
