# Browser configuration for the resubmission

## 1. Create a dedicated public AgentCore Browser

Run from PowerShell:

```powershell
aws bedrock-agentcore-control create-browser `
  --region us-east-1 `
  --name "CustomerSupportBrowser" `
  --description "Public browser for CustomerSupportAgent live web tests" `
  --network-configuration '{"networkMode":"PUBLIC"}'
```

The command returns `browserId`. Copy it.

Check that it is READY:

```powershell
aws bedrock-agentcore-control get-browser `
  --region us-east-1 `
  --browser-id "<BROWSER_ID>"
```

You want:

```text
status: READY
networkMode: PUBLIC
```

AWS documents `PUBLIC` as the network mode that allows the AgentCore Browser to access public internet resources. The custom browser can be used by `AgentCoreBrowser(..., identifier=<BROWSER_ID>)`.

## 2. Deploy with the browser identifier

From the project root:

```powershell
agentcore deploy --yes --env BROWSER_ID="<BROWSER_ID>"
```

The code now reads `BROWSER_ID` and initializes:

```python
AgentCoreBrowser(region=REGION, identifier=BROWSER_ID)
```

If you prefer the AWS-managed browser, the default remains:

```text
aws.browser.v1
```

but the dedicated custom browser is recommended for this resubmission because its network configuration is explicitly PUBLIC.

## 3. Verify the browser from the deployed agent

Use a URL that should return a real page, for example:

```powershell
agentcore invoke --prompt "Use the AgentCore Browser to visit https://example.com and tell me the page title. Do not guess it. Use the live browser result."
```

For the rubric evidence, use the required Amazon/live-web test if your project instructions specify it:

```powershell
agentcore invoke --prompt "Use the AgentCore Browser to visit https://www.amazon.com and tell me the page title. Do not guess it. Use the live browser result."
```

Capture the successful output as:

```text
EVIDENCE SCREENSHOOT\07-browser-live.png
```

## 4. Browser IAM

The runtime execution role should include the browser actions required by the SDK. Recommended browser permissions for this project are:

```text
bedrock-agentcore:StartBrowserSession
bedrock-agentcore:StopBrowserSession
bedrock-agentcore:GetBrowserSession
bedrock-agentcore:UpdateBrowserStream
bedrock-agentcore:ConnectBrowserAutomationStream
bedrock-agentcore:ConnectBrowserLiveViewStream
bedrock-agentcore:InvokeBrowser
bedrock-agentcore:ListBrowsers
```

Do not put AWS access keys or session tokens in the project.
