
SIDErunner
====
A framework for running Selenium IDE tests from within Python without having to export those 
tests.   It reads the tests in their native XML format and makes corresponding webdriver calls 
based on the contents of the XML files.

It can run both tests and test suites.

Installation
----
To use in headless mode you'll need selenium, pyvirtualdisplay and a browser such as FireFox.

    $ apt-get install xvfb xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic
    $ apt-get install pyvirtualdisplay
    $ apt-get install selenium
    $ apt-get install firefox

Then make sure the siderunner library is on your python path.


Example
----
This example runs a simple test suite created with Selenium IDE and saved as .xml files.


    #!/usr/bin/python

    from selenium import webdriver
    from siderunner import SeleniumTestSuite
    from pyvirtualdisplay import Display

    display = Display(visible=1, size=(1920,1024))
    display.start()

    url = 'http://localhost'
    suite = 'basic_tests'

    pathname = 'myproject/mytests/%s' % suite
    driver = webdriver.FireFox()
    driver.implicitly_wait(10)
    try:

        tests = SeleniumTestSuite(pathname)
        try:
            tests.run(driver, url)
        except:
            driver.save_screenshot('%s-suite_error_screen.png' % suite)
    finally:
        driver.quit()
        display.stop()


