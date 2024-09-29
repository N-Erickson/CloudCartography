# Cloud Cartography

## Generate Cloud Infrastructure Maps

Run these scripts against a Terraform State file to generate infrastrucure diagrams.

Diagrams are PNG format. 

```bash
python3 SCRIPT_NAME.py --state=/path/to/tfstate/terraform.tfstate --output=my_infrastructure_diagram
```

These can also be called as part of a GitHub Actions workflow/pipeline. 


GCP:
<img width="699" alt="image" src="https://github.com/user-attachments/assets/493b26a6-bcb8-48f6-9f9f-b3ac27e8d86b">

OCI:
<img width="914" alt="image" src="https://github.com/user-attachments/assets/296d44ec-8409-494b-95bf-400ae175dbd1">



Example Actions workflow that will post to a Pull Request as a comment:
```yaml

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install diagrams
          sudo apt-get update
          sudo apt-get install -y graphviz

      - name: Checkout Diagram Script Repository
        uses: actions/checkout@v3
        with:
          repository: N-Erickson/CloudCartography
          path: CloudCartography

      - name: Generate Infrastructure Diagram
        working-directory: ${{ github.workspace }}
        run: |
          python CloudCartography/<cloud_provider>/<script_name>.py --state=PATH/TO/terraform/terraform.tfstate --output=infra_diagram  # set which provider and paths here

      - name: Get current time
        uses: josStorer/get-current-time@v2
        id: current-time
        with:
          format: YYYY-MM-DD-HH-mm-ss
          utcOffset: "-08:00"

      - name: Create Release
        id: create_release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: infra-diagram-${{ steps.current-time.outputs.formattedTime }}
          release_name: Infrastructure Diagram ${{ steps.current-time.outputs.formattedTime }}
          draft: false
          prerelease: false

      - name: Upload Release Asset
        id: upload-release-asset 
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ./infra_diagram.png
          asset_name: infra_diagram_${{ steps.current-time.outputs.formattedTime }}.png
          asset_content_type: image/png

      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          github-token: ${{secrets.GITHUB_TOKEN}}
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Updated Infrastructure Diagram\n\n![Infrastructure Diagram](${process.env.GITHUB_SERVER_URL}/${context.repo.owner}/${context.repo.repo}/releases/download/infra-diagram-${{ steps.current-time.outputs.formattedTime }}/infra_diagram_${{ steps.current-time.outputs.formattedTime }}.png)`
            })
```
