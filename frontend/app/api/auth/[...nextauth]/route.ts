import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"

// Validate required environment variables at startup
if (process.env.NODE_ENV === 'production') {
  const requiredEnvVars = ['NEXTAUTH_SECRET', 'NEXTAUTH_URL']
  const missing = requiredEnvVars.filter(v => !process.env[v])
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`)
  }
}

const handler = NextAuth({
  debug: process.env.NODE_ENV === 'development',
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code"
        }
      }
    }),
    // SECURITY: Credentials provider disabled by default
    // Uncomment and implement proper authentication if needed
    // For production, use a proper authentication service (Auth0, Firebase, etc.)
    /*
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // SECURITY: Implement proper credential validation
        // Example: Validate against database or identity provider
        if (!credentials?.email || !credentials?.password) {
          return null
        }
        
        // TODO: Implement actual authentication logic
        // Example:
        // const user = await validateUser(credentials.email, credentials.password)
        // if (!user) return null
        // return { id: user.id, email: user.email, name: user.name }
        
        return null // Reject all credentials until properly implemented
      }
    })
    */
  ],
  pages: {
    signIn: "/signin",
    signOut: "/",
    error: "/signin",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id
      }
      return token
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id
      }
      return session
    },
  },
  session: {
    strategy: "jwt",
  },
  secret: process.env.NEXTAUTH_SECRET,
})

export { handler as GET, handler as POST }

