'use client';

import { motion } from 'framer-motion';
import { 
  BoltIcon,
  SpeakerWaveIcon,
  DocumentTextIcon,
  DevicePhoneMobileIcon,
  ClockIcon,
  ChartBarIcon,
  SparklesIcon,
  CloudArrowDownIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';

const features = [
  {
    name: 'AI-Powered Summaries',
    description: 'Advanced language models transform lengthy content into concise, actionable insights while preserving key information.',
    icon: SparklesIcon,
    color: 'from-purple-500 to-purple-700'
  },
  {
    name: 'Audio Briefings',
    description: 'Listen to your content summaries with high-quality, natural-sounding audio generation for hands-free consumption.',
    icon: SpeakerWaveIcon,
    color: 'from-blue-500 to-blue-700'
  },
  {
    name: 'Dual-Format Choice',
    description: 'Switch seamlessly between reading text summaries and listening to audio briefings based on your context.',
    icon: DocumentTextIcon,
    color: 'from-green-500 to-green-700'
  },
  {
    name: 'Mobile-First Design',
    description: 'Optimized for on-the-go consumption with offline capabilities and one-handed navigation.',
    icon: DevicePhoneMobileIcon,
    color: 'from-orange-500 to-orange-700'
  },
  {
    name: 'Smart Prioritization',
    description: 'AI learns your preferences and automatically prioritizes the most relevant content for you.',
    icon: ChartBarIcon,
    color: 'from-red-500 to-red-700'
  },
  {
    name: 'Time-Saving Analytics',
    description: 'Track your reading habits and see exactly how much time you save with intelligent content curation.',
    icon: ClockIcon,
    color: 'from-indigo-500 to-indigo-700'
  },
  {
    name: 'Offline Access',
    description: 'Download content and audio for offline access, ensuring you stay informed anywhere.',
    icon: CloudArrowDownIcon,
    color: 'from-teal-500 to-teal-700'
  },
  {
    name: 'Privacy-First',
    description: 'Your reading habits and data remain private with end-to-end encryption and transparent data practices.',
    icon: ShieldCheckIcon,
    color: 'from-pink-500 to-pink-700'
  },
  {
    name: 'Lightning Fast',
    description: 'Sub-second content loading and processing ensure your information is always up-to-date.',
    icon: BoltIcon,
    color: 'from-yellow-500 to-yellow-700'
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5
    }
  }
};

export default function Features() {
  return (
    <div id="features" className="bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-base font-semibold leading-7 text-primary-600">Everything you need</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Intelligent Content Processing
            </p>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Our platform combines cutting-edge AI with intuitive design to revolutionize how you consume information. 
              Experience the future of content aggregation.
            </p>
          </motion.div>
        </div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="mx-auto mt-16 max-w-2xl sm:mt-20 lg:mt-24 lg:max-w-none"
        >
          <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
            {features.map((feature) => (
              <motion.div
                key={feature.name}
                variants={itemVariants}
                className="flex flex-col group"
              >
                <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${feature.color} group-hover:scale-110 transition-transform duration-200`}>
                    <feature.icon className="h-6 w-6 text-white" aria-hidden="true" />
                  </div>
                  {feature.name}
                </dt>
                <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                  <p className="flex-auto">{feature.description}</p>
                </dd>
              </motion.div>
            ))}
          </dl>
        </motion.div>

        {/* Feature highlight */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mx-auto mt-24 max-w-7xl"
        >
          <div className="relative isolate overflow-hidden bg-gradient-to-b from-primary-100/20 px-6 py-24 shadow-2xl rounded-3xl sm:px-24">
            <h2 className="mx-auto max-w-2xl text-center text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Ready to Transform Your Information Diet?
            </h2>
            <p className="mx-auto mt-6 max-w-xl text-center text-lg leading-8 text-gray-700">
              Join thousands of professionals who have revolutionized their content consumption with AI-powered summaries and audio briefings.
            </p>
            <div className="mx-auto mt-10 flex items-center justify-center gap-x-6">
              <a
                href="#signup"
                className="rounded-lg bg-primary-600 px-6 py-3 text-base font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-colors"
              >
                Start Your Free Trial
              </a>
              <a href="#pricing" className="text-base font-semibold leading-6 text-gray-900 hover:text-primary-600 transition-colors">
                View pricing <span aria-hidden="true">→</span>
              </a>
            </div>
            <div className="absolute -top-24 right-0 -z-10 transform-gpu blur-3xl" aria-hidden="true">
              <div
                className="aspect-[1404/767] w-[87.75rem] bg-gradient-to-r from-primary-400 to-primary-700 opacity-25"
                style={{
                  clipPath:
                    'polygon(73.6% 51.7%, 91.7% 11.8%, 100% 46.4%, 97.4% 82.2%, 92.5% 84.9%, 75.7% 64%, 55.3% 47.5%, 46.5% 49.4%, 45% 62.9%, 50.3% 87.2%, 21.3% 64.1%, 0.1% 100%, 5.4% 51.1%, 21.4% 63.9%, 58.9% 0.2%, 73.6% 51.7%)',
                }}
              />
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}