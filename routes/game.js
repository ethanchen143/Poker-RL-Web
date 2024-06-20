const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

let pythonProcess;
let pendingCallbacks = [];

function startPythonProcess() {
    const scriptPath = path.resolve(__dirname, '../game_flow.py');
    console.log(`Starting Python script at ${scriptPath}`);
  
    pythonProcess = spawn('python3', [scriptPath], {
      cwd: path.resolve(__dirname, '../')
    });
  
    pythonProcess.stdout.on('data', (data) => {
        handlePythonOutput(data.toString());
    });
  
    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python script error: ${data.toString()}`);
    });
  
    pythonProcess.on('close', (code) => {
        console.log(`Python script closed with code ${code}`);
        // Restart the Python process if it closes unexpectedly
        startPythonProcess();
    });
}

function callPython(action, callback) {
    if (!pythonProcess) {
        startPythonProcess();
    }
    
    pendingCallbacks.push(callback);
    pythonProcess.stdin.write(`${action}\n`);
}

function handlePythonOutput(output) {
    const gameStatePath = path.resolve(__dirname, '../game_state.json');
    fs.readFile(gameStatePath, 'utf8', (readErr, data) => {
        if (readErr) {
            console.error(`Error reading game state: ${readErr}`);
            if (pendingCallbacks.length > 0) {
                pendingCallbacks.shift()(null, readErr);
            }
            return;
        }
        const gameState = JSON.parse(data);
        // const filtered = Object.keys(gameState).reduce((acc, key) => {
        //     if (key !== 'deck') {
        //         acc[key] = gameState[key];
        //     }
        //     return acc;
        // }, {});
        // console.log('Parsed game state:', filtered);
        if (pendingCallbacks.length > 0) {
            pendingCallbacks.shift()(gameState, null);
        }
    });
}

// Start the Python process when the server starts
startPythonProcess();

// Route to setup the game
router.get('/', (req, res) => {
  callPython('setup', (gameState, err) => {
      if (err) {
          return res.status(500).send('Error initializing game');
      }
      res.render('game', { game: gameState });
  });
});

// Route to progress the game
router.get('/progress', (req, res) => {
  callPython('progress', (gameState, err) => {
      if (err) {
          return res.status(500).send('Error progressing game');
      }
      res.json(gameState);  
  });
});

router.get('/rec', (req, res) => {
    callPython('rec', (gameState, err) => {
        if (err) {
            return res.status(500).send('Error processing player action');
        }
        res.json(gameState);
    });
});

router.post('/action', (req, res) => {
    const action = req.body.action;
    callPython(`action_${action}`, (gameState, err) => {
        if (err) {
            return res.status(500).send('Error processing player action');
        }
        res.json(gameState);
    });
});

module.exports = router;