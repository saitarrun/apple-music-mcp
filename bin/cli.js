#!/usr/bin/env node

/**
 * apple-music-mcp
 * NPX / Node.js launcher for Apple Music High-Efficiency MCP Server
 */

const { spawn } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);
const isServe = args.length === 0 || args[0] === 'serve';

// Prefer uvx if installed, else fallback to python3
function run() {
  const child = spawn(
    'uvx',
    ['--from', 'git+https://github.com/saitarrun/apple-music-mcp.git', 'apple-music-mcp', ...args],
    {
      stdio: 'inherit',
      env: process.env,
    }
  );

  child.on('error', (err) => {
    if (err.code === 'ENOENT') {
      // uvx not found, fallback to python3
      const pyChild = spawn(
        'python3',
        ['-m', 'apple_music_mcp.server'],
        {
          stdio: 'inherit',
          env: {
            ...process.env,
            PYTHONPATH: path.join(__dirname, '..', 'src'),
          },
        }
      );

      pyChild.on('error', (pyErr) => {
        console.error('Error starting Apple Music MCP server:', pyErr.message);
        console.error('Please ensure Python 3.10+ or uv is installed.');
        process.exit(1);
      });

      pyChild.on('exit', (code) => {
        process.exit(code || 0);
      });
    } else {
      console.error('Error:', err.message);
      process.exit(1);
    }
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

run();
