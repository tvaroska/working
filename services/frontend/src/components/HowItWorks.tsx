'use client';

import { motion } from 'framer-motion';
import { 
  PlusIcon,
  SparklesIcon,
  SpeakerWaveIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

const steps = [
  {
    id: '01',
    title: 'Connect Your Sources',
    description: 'Add your favorite newsletters, blogs, and content sources. We support 500+ popular sources and custom feeds.',
    icon: PlusIcon,
    color: 'from-blue-500 to-blue-700'
  },
  {
    id: '02',
    title: 'AI Processing',
    description: 'Our advanced AI analyzes, summarizes, and prioritizes content based on your preferences and reading history.',
    icon: SparklesIcon,
    color: 'from-purple-500 to-purple-700'
  },
  {
    id: '03',
    title: 'Choose Your Format',
    description: 'Read concise text summaries or listen to audio briefings. Switch between formats anytime, anywhere.',
    icon: SpeakerWaveIcon,
    color: 'from-green-500 to-green-700'
  },
  {
    id: '04',
    title: 'Save Time & Stay Informed',
    description: 'Consume 60% more content in 60% less time. Never miss important updates while staying productive.',
    icon: ClockIcon,
    color: 'from-orange-500 to-orange-700'
  }
];

export default function HowItWorks() {
  return (
    <div id="how-it-works" className="bg-white py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-base font-semibold leading-7 text-primary-600">Simple Process</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              How Updater Works
            </p>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Get started in minutes with our simple 4-step process. No complex setup, no learning curve – just intelligent content at your fingertips.
            </p>
          </motion.div>
        </div>

        <div className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none">
          <div className="grid max-w-xl grid-cols-1 gap-y-16 lg:max-w-none lg:grid-cols-2 lg:gap-x-16 lg:gap-y-20">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="relative flex flex-col lg:flex-row lg:items-center"
              >
                {/* Step number and icon */}
                <div className="flex flex-col items-center lg:items-start lg:flex-row lg:mr-8">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-gray-100 to-gray-200 mb-4 lg:mb-0 lg:mr-6">
                    <span className="text-xl font-bold text-gray-700">{step.id}</span>
                  </div>
                  <div className={`hidden lg:flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${step.color} lg:-ml-3`}>
                    <step.icon className="h-6 w-6 text-white" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 text-center lg:text-left">
                  <h3 className="text-xl font-semibold leading-8 text-gray-900">
                    {step.title}
                  </h3>
                  <p className="mt-4 text-base leading-7 text-gray-600">
                    {step.description}
                  </p>
                </div>

                {/* Mobile icon */}
                <div className={`lg:hidden flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${step.color} mx-auto mt-4`}>
                  <step.icon className="h-6 w-6 text-white" />
                </div>

                {/* Connecting line */}
                {index < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-16 left-20 w-px h-16 bg-gradient-to-b from-gray-300 to-transparent" />
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Demo section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mx-auto mt-24 max-w-4xl"
        >
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-gray-50 to-gray-100 p-8 lg:p-12">
            <div className="text-center">
              <h3 className="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl">
                See It In Action
              </h3>
              <p className="mt-4 text-lg leading-8 text-gray-600">
                Watch how Updater transforms your daily information consumption workflow.
              </p>
              <div className="mt-8">
                <button className="group inline-flex items-center justify-center rounded-xl bg-white px-8 py-4 text-base font-semibold text-gray-900 shadow-sm ring-1 ring-gray-300 hover:bg-gray-50 hover:shadow-md transition-all duration-200">
                  <div className="mr-3 flex h-10 w-10 items-center justify-center rounded-full bg-primary-100 group-hover:bg-primary-200 transition-colors">
                    <svg className="h-5 w-5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                    </svg>
                  </div>
                  Watch 2-minute Demo
                </button>
              </div>
            </div>
            
            {/* Decorative elements */}
            <div className="absolute -top-4 -right-4 h-24 w-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 opacity-10" />
            <div className="absolute -bottom-4 -left-4 h-32 w-32 rounded-full bg-gradient-to-br from-purple-400 to-purple-600 opacity-10" />
          </div>
        </motion.div>
      </div>
    </div>
  );
}