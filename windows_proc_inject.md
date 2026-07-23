https://medium.com/@toneillcodes/windows-process-injection-fundamentals-00d43ee9ecad

|Technique	|Description	|Key Steps|
|-----------|--------------|--------|
|DLL Injection	|Injects a DLL into a running process	|Allocate memory, write DLL path, create remote thread
|Process Hollowing	|Replaces memory of a suspended process with malicious code	|Create process suspended, modify memory, resume process
|Thread Execution Hijacking|	Redirects an existing thread to execute malicious code	|Identify thread, redirect execution flow
|Reflective DLL Injection	|Loads and executes a DLL directly from memory	|Use reflective loader to execute DLL in memory
