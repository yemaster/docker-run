<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docker PHP <?=PHP_VERSION;?> Environment - Docker Run</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        body {
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            text-align: center;
        }

        header {
            margin-bottom: 2rem;
        }

        h1 {
            color: #2d3436;
            margin-bottom: 0.5rem;
            font-size: 2rem;
        }

        .environment-info {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 2rem;
            margin-bottom: 2rem;
            text-align: left;
        }

        .environment-info h2 {
            color: #2d3436;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
        }

        .environment-info h2 i {
            margin-right: 0.5rem;
            color: #777bb4;
        }

        .path-highlight {
            background-color: #f1f1f1;
            padding: 1rem;
            border-radius: 4px;
            font-family: monospace;
            color: #e74c3c;
            font-size: 1.1rem;
            margin: 1rem 0;
            border-left: 4px solid #777bb4;
        }

        .instructions {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 2rem;
            text-align: left;
        }

        .instructions h2 {
            color: #2d3436;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
        }

        .instructions h2 i {
            margin-right: 0.5rem;
            color: #27ae60;
        }

        .instructions ul {
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }

        .instructions li {
            margin-bottom: 0.5rem;
        }

        .command {
            background-color: #2d3436;
            color: #f8f9fa;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-family: monospace;
            display: inline-block;
            margin: 0.5rem 0;
        }

        footer {
            margin-top: 2rem;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Docker Run PHP <?=PHP_VERSION;?></h1>
            <p>PHP 环境测试</p>
        </header>

        <div class="instructions">
            <h2>Getting Started</h2>
            <ul>
                <li>将 PHP 文件放入<code>/var/www/html</code></li>
                <li>访问主机转发端口即可查看</li>
            </ul>
        </div>

        <footer>
            <p>&copy; 2025 Docker Run. PHP <?=PHP_VERSION;?>.</p>
        </footer>
    </div>
</body>
</html>
    