import enum

class HttpResponse(enum.Enum):
  
  OK = (200, "success")
  BAD_REQUEST = (400, "<h1>URL Required<h1>")
  NOT_FOUND = (404, """
        <html>
            <head>
                <title>404 Error</title>
                <style>
                    body {
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .h1-container {
                        margin-top: 40vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                        font-family: Arial, sans-serif;
                    }

                    .h2-container {
                        margin-top: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        text-align: center;
                        font-family: Arial, sans-serif;
                    }

                    h1 {
                        font-size: 36px;
                    }

                    h2 {
                        font-size: 24px;
                    }
                </style>
            </head>
            <div class="h1-container">
                <h1>404 Error</h1>
                </div class="h2-container">
                    <h2>URL Not Found</h2>
                </div>
            </div>
            
            
        </html>
        """)
  CONFLICT = (409, "<h1>Alias already exists<h1>")
  INTERNAL_SERVER_ERROR = (500, "<h1>Internal server error<h1>")
  def __init__(self, code, content):
    self.code = code
    self.content = content

http_code_to_enum = {
  200: HttpResponse.OK,
  400: HttpResponse.BAD_REQUEST,
  404: HttpResponse.NOT_FOUND,
  409: HttpResponse.CONFLICT,
  500: HttpResponse.INTERNAL_SERVER_ERROR,
}
