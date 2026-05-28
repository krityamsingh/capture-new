import { MongoClient } from 'mongodb'

let client
let clientPromise

if (process.env.NODE_ENV === 'development') {
  // In dev: reuse the global client across hot reloads
  if (!global._mongoClientPromise) {
    const uri = process.env.MONGODB_URI
    if (!uri) {
      global._mongoClientPromise = Promise.resolve(null)
    } else {
      client = new MongoClient(uri)
      global._mongoClientPromise = client.connect()
    }
  }
  clientPromise = global._mongoClientPromise
} else {
  // In production (Vercel): lazily connect — never throw at module load time
  clientPromise = new Promise((resolve, reject) => {
    const uri = process.env.MONGODB_URI
    if (!uri) {
      // Return null so routes can handle missing DB gracefully
      return resolve(null)
    }
    const c = new MongoClient(uri)
    c.connect().then(() => resolve(c)).catch(reject)
  })
}

export default clientPromise
