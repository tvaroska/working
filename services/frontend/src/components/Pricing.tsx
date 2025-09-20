'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckIcon, XMarkIcon } from '@heroicons/react/20/solid';
import { SparklesIcon, BoltIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

const plans = [
  {
    name: 'Free',
    id: 'free',
    href: '#signup',
    price: '$0',
    description: 'Perfect for getting started with AI-powered content summaries.',
    features: [
      'AI text summaries',
      'Basic search',
      'Up to 10 sources',
      '50 content pieces per day',
      'Mobile app access',
      'Email support'
    ],
    notIncluded: [
      'Audio summaries',
      'Custom sources',
      'Advanced search',
      'Export capabilities',
      'Priority support'
    ],
    cta: 'Get Started Free',
    popular: false,
    icon: SparklesIcon,
    color: 'gray'
  },
  {
    name: 'Premium',
    id: 'premium',
    href: '#signup',
    price: '$19',
    description: 'For power users and professionals who need advanced features.',
    features: [
      'Everything in Free',
      'AI-generated audio summaries',
      'Custom source processing',
      'Advanced search & filtering',
      'Up to 100 sources',
      '500 content pieces per day',
      'Export to note-taking tools',
      'Offline access',
      'Priority support',
      'Analytics dashboard'
    ],
    notIncluded: [
      'Team sharing',
      'Admin dashboard',
      'API access'
    ],
    cta: 'Start Premium Trial',
    popular: true,
    icon: BoltIcon,
    color: 'primary'
  },
  {
    name: 'Team',
    id: 'team',
    href: '#contact',
    price: '$49',
    description: 'For teams and organizations that need collaboration features.',
    features: [
      'Everything in Premium',
      'Team content sharing',
      'Collaborative bookmarks',
      'Team analytics dashboard',
      'Content assignment workflow',
      'Up to 500 sources',
      '2,000 content pieces per day',
      'Role-based access control',
      'Single Sign-On (SSO)',
      'Dedicated support',
      'API access',
      'Custom integrations'
    ],
    notIncluded: [],
    cta: 'Contact Sales',
    popular: false,
    icon: ShieldCheckIcon,
    color: 'indigo'
  }
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export default function Pricing() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');

  const getPrice = (basePrice: string) => {
    if (basePrice === '$0') return '$0';
    const price = parseInt(basePrice.replace('$', ''));
    if (billingCycle === 'annual') {
      return `$${Math.round(price * 0.8)}`;
    }
    return basePrice;
  };

  const getSavings = (basePrice: string) => {
    if (basePrice === '$0') return '';
    return billingCycle === 'annual' ? 'Save 20%' : '';
  };

  return (
    <div id="pricing" className="bg-gray-50 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-base font-semibold leading-7 text-primary-600">Pricing</h2>
            <p className="mt-2 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
              Choose the Perfect Plan
            </p>
            <p className="mt-6 text-lg leading-8 text-gray-600">
              Start free and upgrade as you grow. All plans include our core AI-powered content processing.
            </p>
          </motion.div>
        </div>

        {/* Billing toggle */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          viewport={{ once: true }}
          className="mt-16 flex justify-center"
        >
          <fieldset className="grid grid-cols-2 gap-x-1 rounded-full p-1 text-center text-xs font-semibold leading-5 ring-1 ring-inset ring-gray-200 bg-white">
            <legend className="sr-only">Payment frequency</legend>
            <label className={classNames(
              billingCycle === 'monthly' ? 'bg-primary-600 text-white' : 'text-gray-500',
              'cursor-pointer rounded-full px-2.5 py-1 transition-colors'
            )}>
              <input
                type="radio"
                name="frequency"
                value="monthly"
                className="sr-only"
                checked={billingCycle === 'monthly'}
                onChange={() => setBillingCycle('monthly')}
              />
              Monthly
            </label>
            <label className={classNames(
              billingCycle === 'annual' ? 'bg-primary-600 text-white' : 'text-gray-500',
              'cursor-pointer rounded-full px-2.5 py-1 transition-colors'
            )}>
              <input
                type="radio"
                name="frequency"
                value="annual"
                className="sr-only"
                checked={billingCycle === 'annual'}
                onChange={() => setBillingCycle('annual')}
              />
              Annual
            </label>
          </fieldset>
        </motion.div>

        {/* Pricing cards */}
        <div className="isolate mx-auto mt-16 grid max-w-md grid-cols-1 gap-y-8 sm:mt-20 lg:mx-0 lg:max-w-none lg:grid-cols-3 lg:gap-x-8 xl:gap-x-12">
          {plans.map((plan, planIdx) => (
            <motion.div
              key={plan.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: planIdx * 0.1 }}
              viewport={{ once: true }}
              className={classNames(
                plan.popular ? 'ring-2 ring-primary-600 scale-105' : 'ring-1 ring-gray-200',
                'rounded-3xl p-8 bg-white shadow-lg hover:shadow-xl transition-all duration-200'
              )}
            >
              <div className="flex items-center justify-between gap-x-4">
                <h3
                  id={plan.id}
                  className={classNames(
                    plan.popular ? 'text-primary-600' : 'text-gray-900',
                    'text-lg font-semibold leading-8'
                  )}
                >
                  {plan.name}
                </h3>
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br ${
                  plan.color === 'primary' ? 'from-primary-500 to-primary-700' :
                  plan.color === 'indigo' ? 'from-indigo-500 to-indigo-700' :
                  'from-gray-400 to-gray-600'
                }`}>
                  <plan.icon className="h-6 w-6 text-white" />
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-gray-600">{plan.description}</p>
              <p className="mt-6 flex items-baseline gap-x-1">
                <span className="text-4xl font-bold tracking-tight text-gray-900">
                  {getPrice(plan.price)}
                </span>
                {plan.price !== '$0' && (
                  <span className="text-sm font-semibold leading-6 text-gray-600">
                    /{billingCycle === 'monthly' ? 'month' : 'year'}
                  </span>
                )}
              </p>
              {getSavings(plan.price) && (
                <p className="mt-2 text-xs font-medium text-green-600">{getSavings(plan.price)}</p>
              )}
              <a
                href={plan.href}
                className={classNames(
                  plan.popular
                    ? 'bg-primary-600 text-white shadow-sm hover:bg-primary-500'
                    : 'text-primary-600 ring-1 ring-inset ring-primary-200 hover:ring-primary-300',
                  'mt-8 block rounded-lg px-3 py-2 text-center text-sm font-semibold leading-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-colors'
                )}
              >
                {plan.cta}
              </a>
              <ul role="list" className="mt-8 space-y-3 text-sm leading-6 text-gray-600">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-x-3">
                    <CheckIcon className="h-6 w-5 flex-none text-primary-600" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
                {plan.notIncluded.map((feature) => (
                  <li key={feature} className="flex gap-x-3 opacity-50">
                    <XMarkIcon className="h-6 w-5 flex-none text-gray-400" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Enterprise section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mx-auto mt-24 max-w-2xl rounded-3xl ring-1 ring-gray-200 bg-white p-8 lg:max-w-4xl lg:p-12"
        >
          <div className="lg:flex lg:items-center lg:gap-x-8">
            <div className="lg:flex-auto">
              <h3 className="text-2xl font-bold tracking-tight text-gray-900">Enterprise</h3>
              <p className="mt-6 text-base leading-7 text-gray-600">
                Need custom solutions, on-premise deployment, or enterprise-grade security? 
                We offer tailored plans for large organizations with specific requirements.
              </p>
              <ul role="list" className="mt-8 grid grid-cols-1 gap-4 text-sm leading-6 text-gray-600 sm:grid-cols-2 sm:gap-6">
                {[
                  'Custom integrations',
                  'On-premise deployment',
                  'Advanced security features',
                  'Dedicated account manager',
                  'SLA guarantees',
                  'Custom data retention',
                  'Unlimited everything',
                  '24/7 priority support'
                ].map((feature) => (
                  <li key={feature} className="flex gap-x-3">
                    <CheckIcon className="h-6 w-5 flex-none text-primary-600" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-10 lg:mt-0 lg:flex-shrink-0">
              <a
                href="#contact"
                className="block rounded-lg bg-gray-900 px-6 py-3 text-center text-base font-semibold text-white shadow-sm hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
              >
                Contact Sales
              </a>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}