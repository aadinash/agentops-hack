// Global variables to track state
let logBuffer = [];
let currentCodeBlock = null;
let outputPath = null;
let finalOutput = null;

// Initialize collapsible elements
document.addEventListener('DOMContentLoaded', () => {
  // Setup collapsible sections
  const collapsibles = document.getElementsByClassName('collapsible');
  for (let i = 0; i < collapsibles.length; i++) {
    collapsibles[i].addEventListener('click', function() {
      this.classList.toggle('active');
      const content = this.nextElementSibling;
      if (content.style.maxHeight) {
        content.style.maxHeight = null;
      } else {
        content.style.maxHeight = content.scrollHeight + 'px';
      }
    });
  }
});

// Fetch available JSONL files
async function fetchFiles() {
  const res = await fetch('/files');
  const files = await res.json();
  const select = document.getElementById('fileSelect');
  select.innerHTML = '';
  files.forEach((f) => {
    const opt = document.createElement('option');
    opt.value = f;
    opt.textContent = f;
    select.appendChild(opt);
  });
}

// Helper to create syntax highlighted code blocks
function syntaxHighlight(code) {
  // This is a simple syntax highlighter for Python
  return code
    .replace(/\b(import|from|def|class|return|for|in|if|else|elif|with|as|True|False|None)\b/g, '<span class="code-keyword">$1</span>')
    .replace(/(['\"])([^'\"]*)\1/g, '<span class="code-string">$1$2$1</span>')
    .replace(/(#.*)$/gm, '<span class="code-comment">$1</span>')
    .replace(/\b(\w+)\(/g, '<span class="code-function">$1</span>(');
}

// Parse and display a code snippet (retained for possible future use)
function displayCodeSnippet(code) {
  const activityLog = document.getElementById('activityLog');
  const codeElement = document.createElement('div');
  codeElement.className = 'code-block';
  codeElement.innerHTML = syntaxHighlight(code);
  activityLog.appendChild(codeElement);
}

// Parse a JSON object or return the original text if not valid JSON
function tryParseJSON(text) {
  try {
    return JSON.parse(text);
  } catch (e) {
    return text;
  }
}

// Process the final output and display relevant sections
function processFinalOutput(output) {
  // Try to parse as JSON
  const result = tryParseJSON(output);
  
  // Check if we have a structured output
  if (typeof result === 'object' && result !== null) {
    // Look for output path in the results
    if (result.output_path) {
      outputPath = result.output_path;
      displayOutputPath(outputPath);
    }
    
    // Check for execution result
    if (result.success !== undefined) {
      displayExecutionResult(result.success, result.message || '');
    }
    
    // Check for agent analysis
    if (result.type === 'code_execution_result' && result.content) {
      displayAgentAnalysis(result);
    }
    
    return;
  }
  
  // Look for patterns in text output
  const pathMatch = output.match(/Cleaned data available at:\s+([^\s]+)/);
  if (pathMatch) {
    outputPath = pathMatch[1];
    displayOutputPath(outputPath);
  }
  
  // Check for success message
  if (output.includes('successfully')) {
    displayExecutionResult(true, 'Python script execution reported as successful.');
  }
}

// Display the output path section
function displayOutputPath(path) {
  const outputPathSection = document.getElementById('outputPathSection');
  const outputPathElement = document.getElementById('outputPath');
  
  outputPathElement.textContent = path;
  outputPathSection.style.display = 'block';
}

// Display execution result (success or failure)
function displayExecutionResult(success, message) {
  const executionOutcome = document.getElementById('executionOutcome');
  const executionResult = document.getElementById('executionResult');
  
  executionResult.className = success ? 'success-message' : 'error-message';
  executionResult.textContent = message || (success ? 
    'Python script execution reported as successful.' : 
    'Python script execution failed.');
  
  executionOutcome.style.display = 'block';
}

// Display agent analysis
function displayAgentAnalysis(data) {
  const agentAnalysisSection = document.getElementById('agentAnalysisSection');
  const agentAnalysis = document.getElementById('agentAnalysis');
  
  agentAnalysis.textContent = data.content;
  agentAnalysisSection.style.display = 'block';
}

// Process incoming log lines
function processLogLine(text) {
  // Check for final output marker
  if (text.startsWith('Final output:')) {
    finalOutput = text.substring('Final output:'.length).trim();
    processFinalOutput(finalOutput);
    return;
  }
  
  // Check for lines that contain Issues and an embedded Current script code block.
  if (text.includes('Issues:') && text.includes('Current script:')) {
    const truncated = text.split('Current script:')[0].trim();
    if (truncated) {
      const activityLog = document.getElementById('activityLog');
      const logLine = document.createElement('div');
      logLine.className = 'agent-item';
      logLine.textContent = truncated;
      activityLog.appendChild(logLine);
    }
    return; // Skip displaying the rest of the long code blob
  }
  
  // Skip raw code blocks if they appear to be Python code snippets
  // but keep other important information like tool calls
  if (!text.includes('[calling tool') && !text.includes('[tool output]') && 
      !text.includes('=== Run') && !text.includes('switched to:') && 
      !text.includes('Cleaned data available')) {
    
    // Skip Python code lines
    if ((text.trim().startsWith('# ') && !text.includes('Issues:')) || 
        text.trim().startsWith('def ') || 
        text.trim().startsWith('import ') || 
        text.trim().startsWith('from ') ||
        text.trim().startsWith('with open') ||
        text.includes('infile:') ||
        text.includes('```python')) {
      return;
    }
    
    // Skip indented code lines and other code-like lines
    if (text.startsWith('    ') || 
        (text.trim().startsWith('return ') && !text.includes('Issues:')) || 
        text.trim().startsWith('for ') || 
        text.trim().startsWith('if ') ||
        (text.includes('=') && !text.includes('Issues:')) ||
        (text.includes('\\n') && !text.includes('```'))) {
      return;
    }
  }
  
  // Handle JSON output
  if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
    try {
      const json = JSON.parse(text);
      if (json.type === 'code_execution_result') {
        displayAgentAnalysis(json);
        return;
      }
    } catch (e) {
      // Not valid JSON, continue processing as text
    }
  }
  
  // Handle tool calls and outputs
  if (text.includes('[calling tool → ')) {
    const activityLog = document.getElementById('activityLog');
    const toolCall = document.createElement('div');
    toolCall.className = 'tool-call';
    toolCall.textContent = text;
    activityLog.appendChild(toolCall);
    return;
  }
  
  if (text.includes('[tool output]')) {
    const activityLog = document.getElementById('activityLog');
    const toolOutput = document.createElement('div');
    toolOutput.className = 'tool-output';
    toolOutput.textContent = text.replace('[tool output] ', '');
    activityLog.appendChild(toolOutput);
    return;
  }
  
  // Check for cleaned output path
  if (text.includes('data available at:')) {
    const match = text.match(/at:\s+([^\s]+)/);
    if (match) {
      outputPath = match[1];
      displayOutputPath(outputPath);
    }
    return;
  }
  
  // Standard log entry
  if (text.trim() !== '') {
    const activityLog = document.getElementById('activityLog');
    const logLine = document.createElement('div');
    logLine.className = 'agent-item';
    logLine.textContent = text;
    activityLog.appendChild(logLine);
  }
}

// Run the cleaner and handle WebSocket communication
async function runCleaner() {
  const filePath = document.getElementById('fileSelect').value;
  const lines = document.getElementById('linesInput').value || 3;

  if (!filePath) {
    alert('Please select an input file.');
    return;
  }
  
  // Reset UI
  document.getElementById('activityLog').innerHTML = '';
  document.getElementById('executionOutcome').style.display = 'none';
  document.getElementById('outputPathSection').style.display = 'none';
  document.getElementById('sampleOutputSection').style.display = 'none';
  document.getElementById('agentAnalysisSection').style.display = 'none';
  
  // Reset state
  logBuffer = [];
  outputPath = null;
  finalOutput = null;
  
  // Create a new connection
  const ws = new WebSocket(`ws://${location.host}/ws`);
  
  ws.onopen = () => {
    ws.send(JSON.stringify({ file_path: filePath, lines: lines }));
  };
  
  ws.onmessage = (ev) => {
    // Process the log line
    processLogLine(ev.data);
  };
  
  ws.onclose = () => {
    // Display any final messages
    if (finalOutput) {
      processFinalOutput(finalOutput);
    }
  };
  
  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
    const activityLog = document.getElementById('activityLog');
    const errorMsg = document.createElement('div');
    errorMsg.className = 'error-message';
    errorMsg.textContent = 'WebSocket error occurred. Please try again.';
    activityLog.appendChild(errorMsg);
  };
}

// Event listeners
document.getElementById('runBtn').addEventListener('click', runCleaner);

// Initialize
fetchFiles();
