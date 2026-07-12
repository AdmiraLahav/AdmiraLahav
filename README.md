class Lahav:
    def __init__(self):
        self.name = "Lav"
        self.alias = "V0lk"
        self.age = 9999
        self.location = "Unknown"
        self.role = "Cybersecurity Student and Developer"

        self.languages = [
            "Python",
            "C#",
            "Java",
            "HTML",
            "CSS",
            "JavaScript",
            "Assembly"
        ]

        self.interests = [
            "Cybersecurity",
            "Artificial Intelligence",
            "Space and Rockets",
            "Military Aviation",
            "Game Development",
            "Blender",
            "Gaming"
        ]

        self.currently_learning = [
            "Web Security",
            "Python",
            "C#",
            "Unity",
            "Linux"
        ]

        self.projects = {
            "GitHub Pages": "Interactive web experiments and tools",
            "Hexdec": "Custom text encoding system",
            "Unity": "Game development and controller systems"
        }

    def introduce(self):
        return (
            f"Hello, I am {self.name}, also known as {self.alias}.\n"
            f"I am a {self.role} from {self.location}.\n"
            f"I enjoy building projects, learning new technologies, "
            f"and understanding how systems work."
        )


profile = Lahav()

print(profile.introduce())

> Goal: Open as many "doors" for the future and later deciding which to go into