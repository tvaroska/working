'use client';

import { motion } from 'framer-motion';
import { StarIcon } from '@heroicons/react/24/solid';

const testimonials = [
  {
    body: 'Updater has completely transformed how I stay informed. I went from spending 2 hours reading newsletters to 30 minutes listening to summaries during my commute. Game changer.',
    author: {
      name: 'Sarah Chen',
      handle: 'sarahchen',
      role: 'Product Manager',
      company: 'TechCorp',
      imageUrl: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  },
  {
    body: 'The AI summaries are incredibly accurate and the audio quality is outstanding. I can finally stay on top of industry news while working out or cooking.',
    author: {
      name: 'Marcus Rodriguez',
      handle: 'marcusr',
      role: 'Engineering Lead',
      company: 'StartupXYZ',
      imageUrl: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  },
  {
    body: 'As a busy executive, Updater helps me stay informed without sacrificing time with my family. The personalization gets better every day.',
    author: {
      name: 'Emily Johnson',
      handle: 'emilyjohnson',
      role: 'VP Strategy',
      company: 'Fortune 500',
      imageUrl: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  },
  {
    body: 'The offline functionality is perfect for my daily train commute. I can download content and listen without worrying about connectivity.',
    author: {
      name: 'David Park',
      handle: 'davidpark',
      role: 'Research Analyst',
      company: 'InvestCorp',
      imageUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  },
  {
    body: 'I love being able to switch between reading and listening modes. Sometimes I want to quickly scan, other times I prefer audio while multitasking.',
    author: {
      name: 'Lisa Thompson',
      handle: 'lisathompson',
      role: 'Marketing Director',
      company: 'GrowthCo',
      imageUrl: 'https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  },
  {
    body: 'The AI learns my preferences incredibly well. It surfaces exactly the content I need and filters out the noise. Impressive technology.',
    author: {
      name: 'James Wilson',
      handle: 'jameswilson',
      role: 'CTO',
      company: 'InnovateNow',
      imageUrl: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
    },
    rating: 5
  }
];

const featuredTestimonial = {
  body: 'Updater has revolutionized our team\'s information consumption. We\'ve increased our industry awareness by 300% while reducing time spent on research by 50%. The ROI is incredible.',
  author: {
    name: 'Alexandra Martinez',
    handle: 'alexmartinez',
    role: 'Chief Strategy Officer',
    company: 'Enterprise Solutions Inc.',
    imageUrl: 'https://images.unsplash.com/photo-1551836022-deb4988cc6c0?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=150&q=80',
  },
  rating: 5
};

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-1">
      {[...Array(5)].map((_, i) => (
        <StarIcon
          key={i}
          className={`h-5 w-5 ${
            i < rating ? 'text-yellow-400' : 'text-gray-300'
          }`}
        />
      ))}
    </div>
  );
}

export default function Testimonials() {
  return (
    <div className="bg-white py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
          >
            <h2 className="text-lg font-semibold leading-8 tracking-tight text-primary-600">Testimonials</h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
              Loved by Professionals Worldwide
            </p>
          </motion.div>
        </div>

        {/* Featured testimonial */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mx-auto mt-16 grid max-w-2xl grid-cols-1 grid-rows-1 gap-8 text-sm leading-6 text-gray-900 sm:mt-20 sm:grid-cols-2 xl:mx-0 xl:max-w-none xl:grid-flow-col xl:grid-cols-4"
        >
          <figure className="col-span-2 hidden sm:block sm:rounded-2xl sm:bg-white sm:shadow-lg sm:ring-1 sm:ring-gray-900/5 xl:col-start-2 xl:row-end-1">
            <blockquote className="p-12 text-xl font-semibold leading-8 tracking-tight text-gray-900">
              <p>"{featuredTestimonial.body}"</p>
            </blockquote>
            <figcaption className="flex items-center gap-x-4 border-t border-gray-900/10 px-6 py-4">
              <img
                className="h-10 w-10 flex-none rounded-full bg-gray-50"
                src={featuredTestimonial.author.imageUrl}
                alt=""
              />
              <div className="flex-auto">
                <div className="font-semibold">{featuredTestimonial.author.name}</div>
                <div className="text-gray-600">{`${featuredTestimonial.author.role}, ${featuredTestimonial.author.company}`}</div>
              </div>
              <StarRating rating={featuredTestimonial.rating} />
            </figcaption>
          </figure>

          {/* Regular testimonials */}
          {testimonials.map((testimonial, testimonialIdx) => (
            <motion.figure
              key={testimonial.author.handle}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: testimonialIdx * 0.1 }}
              viewport={{ once: true }}
              className="flex flex-auto flex-col justify-between rounded-2xl bg-white p-6 shadow-lg ring-1 ring-gray-900/5"
            >
              <blockquote className="text-gray-900">
                <StarRating rating={testimonial.rating} />
                <p className="mt-4">"{testimonial.body}"</p>
              </blockquote>
              <figcaption className="mt-6 flex items-center gap-x-4">
                <img
                  className="h-10 w-10 flex-none rounded-full bg-gray-50"
                  src={testimonial.author.imageUrl}
                  alt=""
                />
                <div className="flex-auto">
                  <div className="font-semibold leading-6 text-gray-900">{testimonial.author.name}</div>
                  <div className="text-sm leading-6 text-gray-600">{`${testimonial.author.role}, ${testimonial.author.company}`}</div>
                </div>
              </figcaption>
            </motion.figure>
          ))}
        </motion.div>

        {/* Stats section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="mx-auto mt-24 max-w-7xl"
        >
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 sm:text-4xl">98%</div>
              <div className="mt-2 text-sm font-medium text-gray-600">User Satisfaction</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 sm:text-4xl">5 hrs</div>
              <div className="mt-2 text-sm font-medium text-gray-600">Saved Per Week</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 sm:text-4xl">60%</div>
              <div className="mt-2 text-sm font-medium text-gray-600">Time Reduction</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-gray-900 sm:text-4xl">10k+</div>
              <div className="mt-2 text-sm font-medium text-gray-600">Active Users</div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}