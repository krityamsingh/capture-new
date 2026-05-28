const { MongoClient } = require('mongodb');
const { spawn } = require('child_process');
const http = require('http');

const MONGODB_URI = "mongodb+srv://krityamwixs:krityamwixs@cluster0.oqvxe2t.mongodb.net/?appName=Cluster0";
const TEST_USER_ID = 888888888;

async function main() {
  console.log("=== 🔒 STARTING INTERACTIVE CONFIRMATION LOGIN INTEGRATION TEST ===");

  const client = new MongoClient(MONGODB_URI);
  await client.connect();
  const db = client.db('Character_catcher');
  const userColl = db.collection('user_collection');

  console.log("🧹 Cleaning up old test users...");
  await userColl.deleteMany({ id: TEST_USER_ID });

  console.log("➕ Creating mock test user in database...");
  await userColl.insertOne({
    id: TEST_USER_ID,
    first_name: "Verification Target",
    gold: 250,
    rubies: 2,
    characters: []
  });

  console.log("🚀 Setup database successfully!");

  // Start Next.js dev server on port 3005
  console.log("Starting Next.js dev server on port 3005...");
  const devServer = spawn('npm', ['run', 'dev'], {
    cwd: '/home/rajput/.gemini/antigravity/scratch/captrue-miniapp',
    env: { ...process.env, PORT: '3005' },
    shell: true
  });

  // Wait for dev server to boot
  await new Promise(resolve => setTimeout(resolve, 5000));
  console.log("Next.js dev server started.");

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
    // TEST 1: Request login verification (sends Telegram request and saves pending in DB)
    console.log("\n🧪 Test 1: Trigger push notification login request...");
    const res1 = await fetchUrl('/api/auth/request', {
      method: 'POST',
      body: { user_id: TEST_USER_ID }
    });
    
    console.log(`Status: ${res1.status}, Response:`, res1.body);
    let requestId = '';
    if (res1.status === 200 && res1.body.ok && res1.body.request_id) {
      requestId = res1.body.request_id;
      console.log(`✅ PASS: Request initiated successfully! Request ID: ${requestId}`);
    } else {
      console.error("❌ FAIL: Could not initiate login request!");
      failedTests++;
    }

    // TEST 2: Poll status right away (should be "pending")
    if (requestId) {
      console.log("\n🧪 Test 2: Poll status immediately...");
      const res2 = await fetchUrl(`/api/auth/poll?request_id=${requestId}`);
      console.log(`Status: ${res2.status}, Response:`, res2.body);
      if (res2.status === 200 && res2.body.status === 'pending') {
        console.log("✅ PASS: Correctly returned status 'pending'!");
      } else {
        console.error(`❌ FAIL: Expected status 'pending', got ${res2.body.status}`);
        failedTests++;
      }

      // TEST 3: Mock the Telegram user tapping "✅ Confirm Login" by posting a callback_query to /api/bot
      console.log("\n🧪 Test 3: Simulating bot callback confirmation ('Confirm Login' click)...");
      const mockCallbackPayload = {
        callback_query: {
          id: "mock_callback_query_id_100",
          message: {
            chat: { id: TEST_USER_ID },
            message_id: 9999
          },
          data: `login_confirm:${requestId}`
        }
      };

      const res3 = await fetchUrl('/api/bot', {
        method: 'POST',
        body: mockCallbackPayload
      });

      console.log(`Status: ${res3.status}, Response:`, res3.body);
      if (res3.status === 200 && res3.body.ok) {
        console.log("✅ PASS: Webhook processed confirmation callback successfully!");
      } else {
        console.error(`❌ FAIL: Webhook callback processing failed with status ${res3.status}`);
        failedTests++;
      }

      // TEST 4: Poll status after confirmation (should be "confirmed" and return auth_token)
      console.log("\n🧪 Test 4: Poll status post-confirmation...");
      const res4 = await fetchUrl(`/api/auth/poll?request_id=${requestId}`);
      console.log(`Status: ${res4.status}, Response:`, res4.body);
      let sessionToken = '';
      if (res4.status === 200 && res4.body.status === 'confirmed' && res4.body.auth_token) {
        sessionToken = res4.body.auth_token;
        console.log(`✅ PASS: Correctly returned status 'confirmed' with session token: ${sessionToken}!`);
      } else {
        console.error(`❌ FAIL: Expected status 'confirmed', got ${res4.body.status}`);
        failedTests++;
      }

      // TEST 5: Verify subsequent poll request returns "expired" because successful request is cleaned up
      console.log("\n🧪 Test 5: Poll status again after successful resolution...");
      const res5 = await fetchUrl(`/api/auth/poll?request_id=${requestId}`);
      console.log(`Status: ${res5.status}, Response:`, res5.body);
      if (res5.status === 200 && res5.body.status === 'expired') {
        console.log("✅ PASS: Successfully cleaned up the pending request from DB (returns expired)!");
      } else {
        console.error(`❌ FAIL: Expected status 'expired', got ${res5.body.status}`);
        failedTests++;
      }

      // TEST 6: Verify API GET /api/user with valid token works, and invalid token returns 401
      if (sessionToken) {
        console.log("\n🧪 Test 6: Verify GET /api/user with valid session token...");
        const res6 = await fetchUrl(`/api/user/${TEST_USER_ID}`, {
          headers: { 'x-auth-token': sessionToken }
        });
        console.log(`Status: ${res6.status}, Body:`, res6.body);
        if (res6.status === 200 && res6.body.gold === 250) {
          console.log("✅ PASS: Profile data fetched correctly!");
        } else {
          console.error("❌ FAIL: Profile fetch failed!");
          failedTests++;
        }

        console.log("\n🧪 Test 7: Verify GET /api/user with invalid session token...");
        const res7 = await fetchUrl(`/api/user/${TEST_USER_ID}`, {
          headers: { 'x-auth-token': 'wrong_token' }
        });
        console.log(`Status: ${res7.status}, Error:`, res7.body.error);
        if (res7.status === 401) {
          console.log("✅ PASS: Mismatched token rejected with 401 Unauthorized!");
        } else {
          console.error("❌ FAIL: Mismatched token was not rejected with 401!");
          failedTests++;
        }
      }
    }

  } catch (err) {
    console.error("Fatal test error:", err);
    failedTests++;
  } finally {
    console.log("\n🧹 Cleaning up database and shutting down dev server...");
    await userColl.deleteMany({ id: TEST_USER_ID });
    await client.close();
    devServer.kill('SIGINT');
  }

  console.log("\n==============================================");
  if (failedTests === 0) {
    console.log("🎉 ALL INTERACTIVE LOGIN TESTS PASSED WITH 100% SUCCESS!");
  } else {
    console.error(`⚠️ TESTS FAILED: ${failedTests} test(s) failed.`);
  }
  console.log("==============================================");
  process.exit(failedTests === 0 ? 0 : 1);
}

main().catch(err => {
  console.error("Fatal error:", err);
  process.exit(1);
});
