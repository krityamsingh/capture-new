const { MongoClient } = require('mongodb');
const { spawn } = require('child_process');
const http = require('http');

const MONGODB_URI = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0";
const TEST_SECURE_ID = 888888888; // Exists but no token
const TEST_OTP_ID = 777777777;    // Exists with valid OTP
const TEST_NONEXISTENT_ID = 999999999; // Does not exist
const OTP_CODE = "555555";
const SECRET = "change_this_secret_key_abc123";

async function main() {
  console.log("=== 🔒 STARTING ID VERIFICATION & SECURITY TEST ===");
  
  // 1. Set up MongoDB state
  const client = new MongoClient(MONGODB_URI);
  await client.connect();
  const db = client.db('Character_catcher');
  const userColl = db.collection('user_collection');

  console.log("🧹 Cleaning up old test users...");
  await userColl.deleteMany({ id: { $in: [TEST_SECURE_ID, TEST_OTP_ID, TEST_NONEXISTENT_ID] } });

  console.log("➕ Creating fresh test users...");
  // Test User 1: Exists, has characters, but no active session token
  await userColl.insertOne({
    id: TEST_SECURE_ID,
    first_name: "Secure Collector",
    gold: 500,
    rubies: 10,
    characters: [{ id: "char_1", name: "Mikasa Ackerman", anime: "Attack on Titan", rarity: "🟠 Rare" }],
    last_ad_watch: null
  });

  // Test User 2: Exists, has a pending OTP verification code
  const expiresAt = new Date(Date.now() + 5 * 60 * 1000); // 5 min
  await userColl.insertOne({
    id: TEST_OTP_ID,
    first_name: "OTP Test User",
    gold: 100,
    rubies: 0,
    characters: [],
    web_login_code: {
      code: OTP_CODE,
      expires_at: expiresAt
    }
  });

  console.log("🚀 Setup database successfully!");

  // 2. Start Next.js Dev Server in Background
  console.log("Starting Next.js dev server...");
  const devServer = spawn('npm', ['run', 'dev'], {
    cwd: '/home/rajput/.gemini/antigravity/scratch/captrue-miniapp',
    env: { ...process.env, PORT: '3005' },
    shell: true
  });

  // Wait for dev server to boot
  await new Promise(resolve => setTimeout(resolve, 5000));
  console.log("Next.js dev server started on port 3005.");

  // Helper function to perform requests
  const fetchUrl = (path, options = {}) => {
    return new Promise((resolve, reject) => {
      const req = http.request({
        hostname: 'localhost',
        port: 3005,
        path: path,
        method: options.method || 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        }
      }, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            body: data ? JSON.parse(data) : null
          });
        });
      });
      req.on('error', reject);
      if (options.body) {
        req.write(JSON.stringify(options.body));
      }
      req.end();
    });
  };

  let failedTests = 0;

  try {
    // TEST 1: Request profile of TEST_SECURE_ID without header (should fail with 401)
    console.log("\n🧪 Test 1: Fetch profile without authentication header...");
    const res1 = await fetchUrl(`/api/user/${TEST_SECURE_ID}`);
    console.log(`Status: ${res1.status}, Error:`, res1.body.error);
    if (res1.status === 401) {
      console.log("✅ PASS: Correctly rejected with 401 Unauthorized!");
    } else {
      console.error(`❌ FAIL: Expected 401, got ${res1.status}`);
      failedTests++;
    }

    // TEST 2: Request profile of TEST_SECURE_ID with invalid token (should fail with 401)
    console.log("\n🧪 Test 2: Fetch profile with invalid auth token...");
    const res2 = await fetchUrl(`/api/user/${TEST_SECURE_ID}`, {
      headers: { 'x-auth-token': 'fake_token_123' }
    });
    console.log(`Status: ${res2.status}, Error:`, res2.body.error);
    if (res2.status === 401) {
      console.log("✅ PASS: Correctly rejected invalid token with 401!");
    } else {
      console.error(`❌ FAIL: Expected 401, got ${res2.status}`);
      failedTests++;
    }

    // TEST 3: Request profile of TEST_NONEXISTENT_ID (should fail with 404 and NOT create user)
    console.log("\n🧪 Test 3: Fetch profile of non-existent user...");
    const res3 = await fetchUrl(`/api/user/${TEST_NONEXISTENT_ID}`);
    console.log(`Status: ${res3.status}, Error:`, res3.body.error);
    if (res3.status === 404) {
      console.log("✅ PASS: Correctly returned 404 Not Found!");
      // Double check MongoDB to ensure it was not created
      const dbCheck = await userColl.findOne({ id: TEST_NONEXISTENT_ID });
      if (!dbCheck) {
        console.log("✅ PASS: User was NOT auto-upserted in the database!");
      } else {
        console.error("❌ FAIL: User was incorrectly upserted in DB!");
        failedTests++;
      }
    } else {
      console.error(`❌ FAIL: Expected 404, got ${res3.status}`);
      failedTests++;
    }

    // TEST 4: Attempt claim for TEST_SECURE_ID with missing/invalid token (should fail with 401)
    console.log("\n🧪 Test 4: Claim character without valid session token...");
    const res4 = await fetchUrl('/api/claim', {
      method: 'POST',
      body: { user_id: TEST_SECURE_ID, secret: SECRET }
    });
    console.log(`Status: ${res4.status}, Msg:`, res4.body.message);
    if (res4.status === 401) {
      console.log("✅ PASS: Claim correctly blocked with 401!");
    } else {
      console.error(`❌ FAIL: Expected 401, got ${res4.status}`);
      failedTests++;
    }

    // TEST 5: Verify login OTP code for TEST_OTP_ID
    console.log("\n🧪 Test 5: Verify login with valid OTP code...");
    const res5 = await fetchUrl('/api/auth/login', {
      method: 'POST',
      body: { user_id: TEST_OTP_ID, code: OTP_CODE }
    });
    console.log(`Status: ${res5.status}, Response:`, res5.body);
    let sessionToken = '';
    if (res5.status === 200 && res5.body.ok && res5.body.auth_token) {
      console.log("✅ PASS: OTP login succeeded and returned session token!");
      sessionToken = res5.body.auth_token;
    } else {
      console.error("❌ FAIL: OTP verification failed!");
      failedTests++;
    }

    // TEST 6: Fetch profile using valid returned session token
    if (sessionToken) {
      console.log("\n🧪 Test 6: Fetch profile with valid session token...");
      const res6 = await fetchUrl(`/api/user/${TEST_OTP_ID}`, {
        headers: { 'x-auth-token': sessionToken }
      });
      console.log(`Status: ${res6.status}, Body:`, res6.body);
      if (res6.status === 200 && res6.body.gold !== undefined) {
        console.log("✅ PASS: Profile fetched successfully with session token!");
      } else {
        console.error(`❌ FAIL: Fetch profile failed! Status ${res6.status}`);
        failedTests++;
      }

      // TEST 7: Fetch profile of OTHER user using our session token (should fail with 401)
      console.log("\n🧪 Test 7: Fetch DIFFERENT profile using our session token...");
      const res7 = await fetchUrl(`/api/user/${TEST_SECURE_ID}`, {
        headers: { 'x-auth-token': sessionToken }
      });
      console.log(`Status: ${res7.status}, Error:`, res7.body.error);
      if (res7.status === 401) {
        console.log("✅ PASS: Mismatched profile access successfully rejected with 401!");
      } else {
        console.error(`❌ FAIL: Mismatched access got status ${res7.status} instead of 401`);
        failedTests++;
      }
    }

  } catch (err) {
    console.error("Test execution error:", err);
    failedTests++;
  } finally {
    // 4. Clean up
    console.log("\n🧹 Cleaning up database and shutting down dev server...");
    await userColl.deleteMany({ id: { $in: [TEST_SECURE_ID, TEST_OTP_ID, TEST_NONEXISTENT_ID] } });
    await client.close();
    devServer.kill('SIGINT');
  }

  console.log("\n==============================================");
  if (failedTests === 0) {
    console.log("🎉 ALL SECURITY CHECKS PASSED WITH 100% SUCCESS!");
  } else {
    console.error(`⚠️ SECURITY CHECKS FAILED: ${failedTests} test(s) failed.`);
  }
  console.log("==============================================");
  process.exit(failedTests === 0 ? 0 : 1);
}

main().catch(err => {
  console.error("Fatal test error:", err);
  process.exit(1);
});
