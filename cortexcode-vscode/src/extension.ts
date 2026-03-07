import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

interface Symbol {
    name: string;
    type: string;
    file: string;
    line: number;
    params?: string[];
    calls?: string[];
    class?: string;
    framework?: string;
}

interface IndexData {
    files: Record<string, { symbols: Symbol[] }>;
    call_graph: Record<string, string[]>;
    project_root: string;
}

let indexData: IndexData | null = null;
let symbolMap: Map<string, Symbol[]> = new Map();
let rootPath: string | null = null;

function loadIndex(rootPath: string): boolean {
    const indexPath = path.join(rootPath, '.cortexcode', 'index.json');
    try {
        if (fs.existsSync(indexPath)) {
            const content = fs.readFileSync(indexPath, 'utf-8');
            const data = JSON.parse(content);
            indexData = data;
            
            symbolMap.clear();
            const files = data.files || {};
            for (const [filePath, fileData] of Object.entries(files)) {
                const symbols = Array.isArray(fileData) ? fileData : (fileData as any).symbols || [];
                for (const sym of symbols) {
                    const existing = symbolMap.get(sym.name) || [];
                    existing.push({ ...sym, file: filePath });
                    symbolMap.set(sym.name, existing);
                }
            }
            return true;
        }
    } catch (e) {
        console.error('Failed to load index:', e);
    }
    return false;
}

function getSymbolAtPosition(document: vscode.TextDocument, position: vscode.Position): Symbol | null {
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) return null;
    
    const word = document.getText(wordRange);
    const symbols = symbolMap.get(word);
    
    if (!symbols || symbols.length === 0) return null;
    
    const currentFile = document.uri.fsPath;
    for (const sym of symbols) {
        if (sym.file && currentFile.endsWith(sym.file.replace(/\//g, path.sep))) {
            return sym;
        }
    }
    
    return symbols[0];
}

async function checkAndInstallCortexCode(): Promise<boolean> {
    return new Promise((resolve) => {
        const proc = require('child_process').spawn('cortexcode', ['--version'], { shell: true });
        let output = '';
        proc.stdout.on('data', (data: string) => { output += data; });
        proc.stderr.on('data', (data: string) => { output += data; });
        proc.on('close', (code: number) => {
            resolve(code === 0);
        });
        proc.on('error', () => { resolve(false); });
    });
}

async function runCortexCodeIndex(rootPath: string): Promise<boolean> {
    return new Promise((resolve) => {
        const proc = require('child_process').spawn('cortexcode', ['index'], { 
            cwd: rootPath, 
            shell: true 
        });
        let output = '';
        proc.stdout.on('data', (data: string) => { output += data; });
        proc.stderr.on('data', (data: string) => { output += data; });
        proc.on('close', (code: number) => {
            console.log('CortexCode index output:', output);
            resolve(code === 0);
        });
        proc.on('error', () => { resolve(false); });
    });
}

export async function activate(context: vscode.ExtensionContext) {
    rootPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || null;
    
    if (!rootPath) {
        vscode.window.showInformationMessage('CortexCode: Open a folder to enable code indexing.');
        return;
    }

    // Check if CortexCode CLI is installed
    const hasCortexCode = await checkAndInstallCortexCode();
    if (!hasCortexCode) {
        const installBtn = 'Install CortexCode';
        const response = await vscode.window.showInformationMessage(
            'CortexCode CLI not found. Install it to enable AI code indexing?',
            installBtn
        );
        if (response === installBtn) {
            vscode.env.openExternal(vscode.Uri.parse('https://pypi.org/project/cortexcode/'));
        }
        return;
    }

    // Check if index already exists
    const indexPath = path.join(rootPath, '.cortexcode', 'index.json');
    if (!fs.existsSync(indexPath)) {
        // Auto-index the project
        const statusMsg = 'CortexCode: Indexing project...';
        vscode.window.showInformationMessage(statusMsg);
        const success = await runCortexCodeIndex(rootPath);
        if (!success) {
            vscode.window.showWarningMessage('CortexCode: Indexing failed. Run "cortexcode index" manually.');
            return;
        }
    }

    // Load the index
    if (rootPath) {
        loadIndex(rootPath);
    }

    // Register hover provider
    const hoverProvider: vscode.HoverProvider = {
        provideHover(document: vscode.TextDocument, position: vscode.Position, token: vscode.CancellationToken) {
            if (!indexData) {
                if (rootPath && loadIndex(rootPath)) {
                    // Index loaded
                } else {
                    return null;
                }
            }
            
            const symbol = getSymbolAtPosition(document, position);
            if (!symbol) return null;
            
            const lines: string[] = [];
            lines.push(`**${symbol.name}** (${symbol.type})`);
            
            if (symbol.framework) {
                lines.push(`Framework: \`${symbol.framework}\``);
            }
            
            if (symbol.params && symbol.params.length > 0) {
                lines.push(`Params: \`${symbol.params.join(', ')}\``);
            }
            
            if (symbol.class) {
                lines.push(`Class: \`${symbol.class}\``);
            }
            
            lines.push(`File: \`${symbol.file}:${symbol.line}\``);
            
            if (symbol.calls && symbol.calls.length > 0) {
                lines.push(`Calls: ${symbol.calls.slice(0, 5).join(', ')}${symbol.calls.length > 5 ? '...' : ''}`);
            }
            
            const callGraph = indexData?.call_graph || {};
            const callers = Object.entries(callGraph)
                .filter(([_, calls]) => calls.includes(symbol.name))
                .map(([name, _]) => name)
                .slice(0, 5);
            
            if (callers.length > 0) {
                lines.push(`Called by: ${callers.join(', ')}`);
            }
            
            return new vscode.Hover(lines.join('\n\n'));
        }
    };
    
    // Register for all document types
    const languages = ['javascript', 'javascriptreact', 'typescript', 'typescriptreact', 'python', 'java', 'go', 'rust', 'csharp'];
    for (const lang of languages) {
        context.subscriptions.push(vscode.languages.registerHoverProvider({ language: lang }, hoverProvider));
    }

    // Register go-to-definition
    const definitionProvider: vscode.DefinitionProvider = {
        provideDefinition(document: vscode.TextDocument, position: vscode.Position, token: vscode.CancellationToken) {
            if (!indexData && rootPath) {
                loadIndex(rootPath);
            }
            
            const symbol = getSymbolAtPosition(document, position);
            if (!symbol || !symbol.file || !symbol.line) return null;
            
            const fullPath = rootPath ? path.join(rootPath, symbol.file) : symbol.file;
            
            try {
                if (fs.existsSync(fullPath)) {
                    const uri = vscode.Uri.file(fullPath);
                    const range = new vscode.Range(symbol.line - 1, 0, symbol.line - 1, 0);
                    return new vscode.Location(uri, range);
                }
            } catch (e) {
                // File not found
            }
            
            return null;
        }
    };
    
    for (const lang of languages) {
        context.subscriptions.push(vscode.languages.registerDefinitionProvider({ language: lang }, definitionProvider));
    }

    // Command: Index workspace
    const indexCommand = vscode.commands.registerCommand('cortexcode.index', async () => {
        if (!rootPath) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        const terminal = vscode.window.createTerminal('CortexCode Index');
        terminal.sendText(`cd "${rootPath}" && cortexcode index`);
        terminal.show();
    });

    // Command: Generate docs
    const docsCommand = vscode.commands.registerCommand('cortexcode.docs', async () => {
        if (!rootPath) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        const terminal = vscode.window.createTerminal('CortexCode Docs');
        terminal.sendText(`cd "${rootPath}" && cortexcode docs --open`);
        terminal.show();
    });

    // Command: Generate wiki
    const wikiCommand = vscode.commands.registerCommand('cortexcode.wiki', async () => {
        if (!rootPath) {
            vscode.window.showErrorMessage('No workspace folder found');
            return;
        }

        const terminal = vscode.window.createTerminal('CortexCode Wiki');
        terminal.sendText(`cd "${rootPath}" && cortexcode wiki --open`);
        terminal.show();
    });

    // Command: Get context for symbol
    const contextCommand = vscode.commands.registerCommand('cortexcode.getContext', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage('No active editor');
            return;
        }
        
        const position = editor.selection.active;
        const symbol = getSymbolAtPosition(editor.document, position);
        
        if (!symbol) {
            vscode.window.showInformationMessage('No symbol found at cursor. Hover over a function/class to see info.');
            return;
        }
        
        const callGraph = indexData?.call_graph || {};
        const callers = Object.entries(callGraph)
            .filter(([_, calls]) => calls.includes(symbol.name))
            .map(([name, _]) => name);
        
        const content = [
            `# ${symbol.name}`,
            ``,
            `**Type:** ${symbol.type}`,
            `**File:** ${symbol.file}:${symbol.line}`,
            symbol.framework ? `**Framework:** ${symbol.framework}` : '',
            symbol.class ? `**Class:** ${symbol.class}` : '',
            symbol.params?.length ? `**Params:** ${symbol.params.join(', ')}` : '',
            '',
            `## Calls`,
            symbol.calls?.length ? symbol.calls.join('\n') : 'None',
            '',
            `## Called By`,
            callers.length ? callers.join('\n') : 'None',
        ].filter(Boolean).join('\n');
        
        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown'
        });
        await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside });
    });

    // Command: Show all symbols
    const symbolsCommand = vscode.commands.registerCommand('cortexcode.showSymbols', async () => {
        if (!indexData) {
            if (rootPath && !loadIndex(rootPath)) {
                vscode.window.showErrorMessage('Run "cortexcode index" first');
                return;
            }
        }
        
        const symbols: string[] = [];
        for (const [name, syms] of symbolMap.entries()) {
            const sym = syms[0];
            symbols.push(`- \`${sym.type}\` **${name}** - ${sym.file}:${sym.line}`);
        }
        
        const content = [
            `# CortexCode Symbols`,
            ``,
            `Total: ${symbolMap.size} symbols`,
            ``,
            ...symbols.sort(),
        ].join('\n');
        
        const doc = await vscode.workspace.openTextDocument({
            content,
            language: 'markdown'
        });
        await vscode.window.showTextDocument(doc);
    });

    // Status bar
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.text = `$(code) CortexCode: ${symbolMap.size} symbols`;
    statusBar.command = 'cortexcode.showSymbols';
    statusBar.tooltip = 'Click to see all symbols';
    statusBar.show();

    // ─── Copilot Chat Participant ───
    const chatHandler: vscode.ChatRequestHandler = async (
        request: vscode.ChatRequest,
        chatContext: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> => {
        // Try to load index if not loaded
        if (!indexData && rootPath) {
            loadIndex(rootPath);
        }
        
        if (!indexData) {
            stream.markdown(`# CortexCode\n\n**No index found in this workspace.**\n\nTo get started:\n1. Run \`cortexcode index\` in the terminal\n2. Or use the command palette: *CortexCode: Index Project*\n\nThis will create a \`.cortexcode/index.json\` file that powers the chat.`);
            return {};
        }

        const query = request.prompt.trim();
        const command = request.command;

        if (command === 'search' || (!command && query)) {
            return handleSearch(query, stream);
        } else if (command === 'context') {
            return handleContext(query, stream);
        } else if (command === 'impact') {
            return handleImpact(query, stream);
        } else if (command === 'deadcode') {
            return handleDeadCode(stream);
        } else if (command === 'complexity') {
            return handleComplexity(stream);
        } else if (!query && !command) {
            // Default welcome message
            stream.markdown(`# CortexCode\n\n**Code indexing for AI assistants**\n\nAvailable commands:\n- \`@cortexcode search <name>\` — Find symbols\n- \`@cortexcode /context <query>\` — Get relevant code\n- \`@cortexcode /impact <symbol>\` — See what breaks if you change it\n- \`@cortexcode /deadcode\` — Find unused symbols\n- \`@cortexcode /complexity\` — View complex functions\n\n**Stats:** ${symbolMap.size} symbols indexed`);
            return {};
        } else {
            // Default: treat as search
            return handleSearch(query, stream);
        }
    };

    let chatParticipant: vscode.ChatParticipant | undefined;
    try {
        chatParticipant = vscode.chat.createChatParticipant('cortexcode.chat', chatHandler);
        chatParticipant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'icon.png');
    } catch (e) {
        console.error('Failed to create chat participant:', e);
    }

    context.subscriptions.push(indexCommand, docsCommand, wikiCommand, contextCommand, symbolsCommand, statusBar);
    if (chatParticipant) {
        context.subscriptions.push(chatParticipant);
    }

    // Watch for file changes to reload index
    const watcher = vscode.workspace.createFileSystemWatcher('**/.cortexcode/index.json');
    watcher.onDidChange(() => {
        if (rootPath) {
            loadIndex(rootPath);
            statusBar.text = `$(code) CortexCode: ${symbolMap.size} symbols`;
        }
    });
}

// ─── Chat Helpers ───

function getSourceCode(filePath: string, line: number, context: number = 15): string | null {
    if (!rootPath) { return null; }
    const fullPath = path.join(rootPath, filePath);
    try {
        if (!fs.existsSync(fullPath)) { return null; }
        const content = fs.readFileSync(fullPath, 'utf-8');
        const lines = content.split('\n');
        const start = Math.max(0, line - 1 - context);
        const end = Math.min(lines.length, line - 1 + context);
        return lines.slice(start, end).join('\n');
    } catch { return null; }
}

function insertAsCopilotContext(stream: vscode.ChatResponseStream, filePath: string, line: number, name: string): void {
    const code = getSourceCode(filePath, line, 20);
    if (code) {
        const ext = path.extname(filePath).slice(1) || 'text';
        stream.markdown(`**📄 ${path.basename(filePath)}:${line}**\n\`\`\`${ext}\n${code}\n\`\`\`\n`);
    }
}

// ─── Chat Handlers ───

function handleSearch(query: string, stream: vscode.ChatResponseStream): vscode.ChatResult {
    const queryLower = query.toLowerCase();
    const matches: Symbol[] = [];

    for (const [name, syms] of symbolMap.entries()) {
        if (name.toLowerCase().includes(queryLower)) {
            matches.push(...syms);
        }
    }

    if (matches.length === 0) {
        stream.markdown(`No symbols found matching **"${query}"**.`);
        return {};
    }

    stream.markdown(`### Found ${matches.length} symbols matching "${query}"\n\n`);
    
    // Include source code for top 5 results
    const topResults = matches.slice(0, 5);
    for (const sym of topResults) {
        const fw = sym.framework ? ` \`${sym.framework}\`` : '';
        stream.markdown(`- \`${sym.type}\` **${sym.name}**${fw} — \`${sym.file}:${sym.line}\`\n`);
        if (sym.params && sym.params.length > 0) {
            stream.markdown(`  Params: \`${sym.params.join(', ')}\`\n`);
        }
        if (sym.calls && sym.calls.length > 0) {
            stream.markdown(`  Calls: ${sym.calls.slice(0, 5).map(c => `\`${c}\``).join(', ')}\n`);
        }
        // Add source code
        insertAsCopilotContext(stream, sym.file, sym.line, sym.name);
    }
    
    // List remaining without code
    if (matches.length > 5) {
        stream.markdown(`\n**More matches:**\n`);
        for (const sym of matches.slice(5, 30)) {
            const fw = sym.framework ? ` \`${sym.framework}\`` : '';
            stream.markdown(`- \`${sym.type}\` **${sym.name}**${fw} — \`${sym.file}:${sym.line}\`\n`);
        }
    }
    if (matches.length > 30) {
        stream.markdown(`\n*...and ${matches.length - 30} more*\n`);
    }
    return {};
}

function handleContext(query: string, stream: vscode.ChatResponseStream): vscode.ChatResult {
    if (!indexData) { return {}; }

    const queryLower = query.toLowerCase();
    const relevant: { sym: Symbol; score: number }[] = [];

    for (const [name, syms] of symbolMap.entries()) {
        for (const sym of syms) {
            let score = 0;
            if (name.toLowerCase() === queryLower) { score = 10; }
            else if (name.toLowerCase().includes(queryLower)) { score = 5; }
            else if (sym.file.toLowerCase().includes(queryLower)) { score = 3; }
            
            // Boost by call graph connectivity
            const callees = indexData.call_graph[name] || [];
            score += Math.min(callees.length, 3);

            if (score > 0) {
                relevant.push({ sym, score });
            }
        }
    }

    relevant.sort((a, b) => b.score - a.score);
    const top = relevant.slice(0, 20);

    if (top.length === 0) {
        stream.markdown(`No context found for **"${query}"**. Try a different query.`);
        return {};
    }

    stream.markdown(`### Context for "${query}"\n\n`);
    stream.markdown(`*${top.length} relevant symbols (ranked by relevance + connectivity)*\n\n`);

    // Include source code for top 5 results
    for (const { sym, score } of top.slice(0, 5)) {
        stream.markdown(`#### ${sym.name} \`${sym.type}\`\n`);
        stream.markdown(`- **File:** \`${sym.file}:${sym.line}\`\n`);
        if (sym.framework) { stream.markdown(`- **Framework:** \`${sym.framework}\`\n`); }
        if (sym.params && sym.params.length) { stream.markdown(`- **Params:** \`${sym.params.join(', ')}\`\n`); }
        if (sym.calls && sym.calls.length) { stream.markdown(`- **Calls:** ${sym.calls.slice(0, 8).map(c => `\`${c}\``).join(', ')}\n`); }
        // Add source code
        insertAsCopilotContext(stream, sym.file, sym.line, sym.name);
    }
    
    // List remaining without code
    if (top.length > 5) {
        stream.markdown(`\n**More results:**\n`);
        for (const { sym } of top.slice(5, 20)) {
            stream.markdown(`- \`${sym.type}\` **${sym.name}** — \`${sym.file}:${sym.line}\`\n`);
        }
    }
    return {};
}

function handleImpact(symbolName: string, stream: vscode.ChatResponseStream): vscode.ChatResult {
    if (!indexData) { return {}; }

    const callGraph = indexData.call_graph || {};

    // Build reverse graph
    const reverseGraph: Record<string, string[]> = {};
    for (const [caller, callees] of Object.entries(callGraph)) {
        for (const callee of callees) {
            if (!reverseGraph[callee]) { reverseGraph[callee] = []; }
            reverseGraph[callee].push(caller);
        }
    }

    const directCallers = reverseGraph[symbolName] || [];
    const indirectCallers = new Set<string>();
    for (const dc of directCallers) {
        for (const caller of (reverseGraph[dc] || [])) {
            if (caller !== symbolName && !directCallers.includes(caller)) {
                indirectCallers.add(caller);
            }
        }
    }

    const total = directCallers.length + indirectCallers.size;
    const risk = total > 10 ? 'HIGH' : total > 3 ? 'MEDIUM' : 'LOW';

    stream.markdown(`### Change Impact: \`${symbolName}\`\n\n`);
    stream.markdown(`**Risk:** ${risk} | **Total affected:** ${total} symbols\n\n`);

    // Add source code for the symbol itself
    const targetSyms = symbolMap.get(symbolName) || [];
    if (targetSyms.length > 0) {
        insertAsCopilotContext(stream, targetSyms[0].file, targetSyms[0].line, symbolName);
    }

    if (directCallers.length > 0) {
        stream.markdown(`**Direct callers (${directCallers.length}):**\n`);
        for (const c of directCallers) { stream.markdown(`- \`${c}\`\n`); }
        stream.markdown('\n');
    }
    if (indirectCallers.size > 0) {
        stream.markdown(`**Indirect callers (${indirectCallers.size}):**\n`);
        for (const c of indirectCallers) { stream.markdown(`- \`${c}\`\n`); }
    }
    if (total === 0) {
        stream.markdown(`*No other symbols call \`${symbolName}\`.*\n`);
    }
    return {};
}

function handleDeadCode(stream: vscode.ChatResponseStream): vscode.ChatResult {
    if (!indexData) { return {}; }

    const callGraph = indexData.call_graph || {};
    const allCalled = new Set<string>();
    for (const callees of Object.values(callGraph)) {
        for (const c of callees) { allCalled.add(c); }
    }

    const dead: Symbol[] = [];
    for (const [name, syms] of symbolMap.entries()) {
        if (allCalled.has(name)) { continue; }
        const sym = syms[0];
        if (sym.framework) { continue; } // Framework-wired
        if (sym.type === 'class') { continue; }
        if (['main', 'app', 'init', 'setup', 'handler', 'default', 'index'].includes(name.toLowerCase())) { continue; }
        if (name.startsWith('__') && name.endsWith('__')) { continue; }
        if (sym.file.includes('test') || sym.file.includes('spec')) { continue; }
        dead.push(sym);
    }

    stream.markdown(`### Potentially Unused Symbols\n\n`);
    stream.markdown(`Found **${dead.length}** symbols that are never called by other indexed code.\n\n`);

    // Include source code for top 5 dead symbols
    for (const sym of dead.slice(0, 5)) {
        stream.markdown(`- \`${sym.type}\` **${sym.name}** — \`${sym.file}:${sym.line}\`\n`);
        insertAsCopilotContext(stream, sym.file, sym.line, sym.name);
    }
    
    // List remaining without code
    if (dead.length > 5) {
        stream.markdown(`\n**More:**\n`);
        for (const sym of dead.slice(5, 30)) {
            stream.markdown(`- \`${sym.type}\` **${sym.name}** — \`${sym.file}:${sym.line}\`\n`);
        }
    }
    if (dead.length > 30) {
        stream.markdown(`\n*...and ${dead.length - 30} more*\n`);
    }
    return {};
}

function handleComplexity(stream: vscode.ChatResponseStream): vscode.ChatResult {
    if (!indexData) { return {}; }

    const funcs: { name: string; file: string; line: number; params: number; calls: number }[] = [];
    for (const [name, syms] of symbolMap.entries()) {
        for (const sym of syms) {
            if (sym.type === 'function' || sym.type === 'method') {
                funcs.push({
                    name,
                    file: sym.file,
                    line: sym.line,
                    params: (sym.params || []).length,
                    calls: (sym.calls || []).length,
                });
            }
        }
    }

    // Score by params + calls (simple heuristic without source access)
    funcs.sort((a, b) => (b.params + b.calls) - (a.params + a.calls));

    stream.markdown(`### Most Complex Functions\n\n`);
    stream.markdown(`*Ranked by parameter count + outgoing calls (heuristic without source)*\n\n`);

    // Include source code for top 5 complex functions
    for (const f of funcs.slice(0, 5)) {
        stream.markdown(`**${f.name}** — ${f.params} params, ${f.calls} calls — \`${f.file}:${f.line}\`\n`);
        insertAsCopilotContext(stream, f.file, f.line, f.name);
    }
    
    // Table for remaining
    if (funcs.length > 5) {
        stream.markdown(`\n| Function | Params | Calls | File |\n`);
        stream.markdown(`|----------|--------|-------|------|\n`);
        for (const f of funcs.slice(5, 20)) {
            stream.markdown(`| **${f.name}** | ${f.params} | ${f.calls} | \`${f.file}:${f.line}\` |\n`);
        }
    }
    return {};
}

export function deactivate() {}
