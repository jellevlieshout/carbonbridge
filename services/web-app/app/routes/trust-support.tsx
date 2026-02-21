import React, { useEffect, useRef, useState } from 'react';
import gsap from 'gsap';
import { HelpCircle, Mail, MessageCircle, BookOpen, ChevronDown, ExternalLink, FileText, Video } from 'lucide-react';
import type { Route } from "./+types/trust-support";

export function meta({ }: Route.MetaArgs) {
    return [
        { title: "CarbonBridge | Support Center" },
        { name: "description", content: "Get help with your CarbonBridge account, carbon credit purchases, and platform features." },
    ];
}

const faqs = [
    {
        question: 'How are carbon credits verified on CarbonBridge?',
        answer: 'Every credit listed on CarbonBridge has been validated and verified by an accredited third-party auditor under internationally recognized standards (VCS, Gold Standard, ACR, or CAR). We apply additional internal screening including project risk scoring, co-benefit assessment, and permanence buffer analysis.',
    },
    {
        question: 'What happens when I purchase a carbon credit?',
        answer: 'When you purchase credits, CarbonBridge processes your payment via Stripe, reserves the corresponding credits on the source registry, and transfers them to your CarbonBridge portfolio. You can then hold, retire, or re-sell these credits at any time.',
    },
    {
        question: 'Can I retire credits directly through the platform?',
        answer: 'Yes. CarbonBridge supports direct retirement of credits on their source registry. When you retire a credit, it is permanently removed from circulation and cannot be re-sold. You will receive a retirement certificate with the serial numbers, project details, and vintage year.',
    },
    {
        question: 'How does the autonomous purchasing agent work?',
        answer: 'The CarbonBridge Agent uses AI to continuously monitor the voluntary carbon market on your behalf. Based on your configured preferences (budget, project types, registries, co-benefits), it identifies optimal purchasing opportunities and can execute trades automatically within your approved parameters.',
    },
    {
        question: 'What reporting formats are supported?',
        answer: 'CarbonBridge supports CSV/Excel exports for data analysis, formatted PDF reports for presentations, and XBRL/iXBRL machine-readable disclosures for regulatory submissions. Reports are aligned with GHG Protocol, CDP, TCFD, and CSRD/ESRS frameworks.',
    },
    {
        question: 'Is CarbonBridge suitable for compliance markets?',
        answer: 'CarbonBridge currently focuses on the voluntary carbon market (VCM). While our credits are not directly fungible in compliance markets like the EU ETS, many of our supported registries issue CORSIA-eligible credits. We provide audit-ready documentation compatible with compliance reporting requirements.',
    },
    {
        question: 'How do I set my budget and purchasing preferences?',
        answer: 'Navigate to the Purchase Wizard from the sidebar to set your annual CO₂ offset target, budget per tonne, preferred project types, and registry preferences. The agent will use these preferences to identify and execute optimal trades on your behalf.',
    },
    {
        question: 'What is a vintage year and why does it matter?',
        answer: 'The vintage year indicates when the emission reduction or removal actually took place. More recent vintages are generally preferred as they represent current environmental impact. Some compliance frameworks and corporate policies require credits from specific vintage periods.',
    },
];

const contactChannels = [
    {
        icon: Mail,
        title: 'Email Support',
        description: 'Detailed inquiries, account issues, and documentation requests.',
        action: 'support@carbonbridge.io',
        actionLabel: 'Send Email',
    },
    {
        icon: MessageCircle,
        title: 'Live Chat',
        description: 'Quick questions and real-time assistance during business hours (CET).',
        action: '#',
        actionLabel: 'Start Chat',
    },
];

const resources = [
    { icon: BookOpen, title: 'Platform Documentation', description: 'Comprehensive guides for all CarbonBridge features and workflows.' },
    { icon: FileText, title: 'API Reference', description: 'RESTful API docs for programmatic access to your portfolio and market data.' },
    { icon: Video, title: 'Video Tutorials', description: 'Step-by-step walkthroughs for common platform tasks and agent configuration.' },
];

export default function TrustSupportPage() {
    const containerRef = useRef<HTMLDivElement>(null);
    const [openFaq, setOpenFaq] = useState<number | null>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(".page-stagger", { y: 30, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.12, duration: 0.8, ease: "power3.out", delay: 0.1 });
        }, containerRef);
        return () => ctx.revert();
    }, []);

    return (
        <div ref={containerRef} className="flex flex-col gap-10 w-full animate-in fade-in duration-700">
            {/* Hero */}
            <div className="page-stagger relative w-full rounded-[2rem] bg-canopy text-linen p-10 overflow-hidden shadow-sm">
                <div className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay z-0" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")" }} />
                <div className="absolute inset-0 z-0 bg-[radial-gradient(circle_at_80%_0%,rgba(61,107,82,0.4)_0%,transparent_50%)] pointer-events-none" />

                <div className="relative z-10 flex flex-col gap-4">
                    <h1 className="text-[3rem] leading-tight tracking-tight font-serif italic text-linen">Support Center</h1>
                    <p className="text-linen/70 font-sans text-lg max-w-2xl">
                        Find answers to common questions, reach our team, or explore platform documentation.
                    </p>
                </div>
            </div>

            {/* FAQ Accordion */}
            <div className="page-stagger flex flex-col gap-4">
                <h2 className="text-xl font-semibold text-slate mb-2">Frequently Asked Questions</h2>
                <div className="flex flex-col gap-2">
                    {faqs.map((faq, index) => (
                        <div key={index} className="bg-white border border-mist rounded-2xl shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                            <button
                                onClick={() => setOpenFaq(openFaq === index ? null : index)}
                                className="w-full flex items-center justify-between p-6 text-left cursor-pointer group"
                            >
                                <span className="font-sans font-medium text-slate pr-4">{faq.question}</span>
                                <ChevronDown
                                    size={18}
                                    className={`text-slate/40 shrink-0 transition-transform duration-300 ${openFaq === index ? 'rotate-180' : ''}`}
                                />
                            </button>
                            <div className={`overflow-hidden transition-all duration-300 ${openFaq === index ? 'max-h-96 pb-6' : 'max-h-0'}`}>
                                <div className="px-6">
                                    <div className="border-t border-mist pt-4">
                                        <p className="font-sans text-sm text-slate/70 leading-relaxed">{faq.answer}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Contact Channels */}
            <div className="page-stagger flex flex-col gap-4">
                <h2 className="text-xl font-semibold text-slate mb-2">Contact Us</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {contactChannels.map((channel) => (
                        <div key={channel.title} className="bg-white border border-mist rounded-2xl p-8 shadow-sm hover:shadow-md transition-shadow flex flex-col gap-4">
                            <div className="w-12 h-12 rounded-xl bg-canopy/5 border border-canopy/20 flex items-center justify-center">
                                <channel.icon size={24} className="text-canopy" />
                            </div>
                            <div>
                                <h3 className="font-sans font-bold text-slate text-lg mb-1">{channel.title}</h3>
                                <p className="font-sans text-sm text-slate/60 leading-relaxed">{channel.description}</p>
                            </div>
                            <button className="mt-auto w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-canopy/5 text-canopy font-medium text-sm border border-canopy/20 hover:bg-canopy hover:text-linen transition-colors cursor-pointer">
                                {channel.actionLabel}
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Documentation Resources */}
            <div className="page-stagger flex flex-col gap-4">
                <h2 className="text-xl font-semibold text-slate mb-2">Documentation & Resources</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {resources.map((resource) => (
                        <div key={resource.title} className="bg-white border border-mist rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow group cursor-pointer">
                            <div className="flex items-start justify-between mb-4">
                                <div className="w-10 h-10 rounded-xl bg-mist/50 flex items-center justify-center">
                                    <resource.icon size={20} className="text-slate/60" />
                                </div>
                                <ExternalLink size={14} className="text-slate/20 group-hover:text-canopy transition-colors" />
                            </div>
                            <h4 className="font-sans font-semibold text-slate mb-1">{resource.title}</h4>
                            <p className="font-sans text-sm text-slate/60 leading-relaxed">{resource.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
