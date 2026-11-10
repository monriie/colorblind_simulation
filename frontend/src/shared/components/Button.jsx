import { motion } from 'framer-motion'

const VARIANTS = {
  primary: 'bg-primary text-on-primary hover:bg-primary-container',
  secondary: 'border border-outline-variant bg-white text-on-surface hover:border-primary',
}

const SIZES = {
  sm: 'rounded px-4 py-2 text-sm',
  md: 'rounded-lg px-6 py-3',
  lg: 'rounded-xl px-8 py-4 text-lg',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...props
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      className={`font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${SIZES[size]} ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  )
}

