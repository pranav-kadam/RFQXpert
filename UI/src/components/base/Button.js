import { cn } from "@/lib/utils";
import { Icon } from "@iconify/react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

export function Button({
  href,
  icon,
  leading,
  label,
  size = "base",
  color = "dark",
  variant = "solid",
  block = false,
  onClick,
  className,
  openFile = false, // Enable file picker
}) {
  const inputRef = useRef(null);
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = (e) => {
    if (openFile) {
      e.preventDefault();
      inputRef.current?.click();
    } else if (onClick) {
      onClick(e);
    }
  };

  const handleFileChange = async (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === "application/pdf") {
        setIsLoading(true);
        const formData = new FormData();
        formData.append("file", file);
        
        try {
          const response = await fetch("http://localhost:8000/upload", {
            method: "POST",
            body: formData,
          });
          
          if (response.ok) {
            const result = await response.json();
            console.log("Upload successful:", result);
            router.push("/upload");
          } else {
            const errorData = await response.json();
            console.error("Upload failed:", errorData);
            alert("Upload failed: " + (errorData.error || "Unknown error"));
          }
        } catch (err) {
          console.error("Upload error:", err);
          alert("An error occurred while uploading: " + err.message);
        } finally {
          setIsLoading(false);
          // Clear the input to allow uploading the same file again
          if (inputRef.current) {
            inputRef.current.value = "";
          }
        }
      } else {
        alert("Only PDF files are allowed.");
      }
    }
  };
  
  const iconClass = cn(
    { "size-5": size === "base" },
    { "size-4": size === "small" },
    { "group-hover:translate-x-1 duration-100 ease-in-out": variant === "link" }
  );

  const Tag = href && !openFile ? "a" : "button";
  
  return (
    <>
      <Tag
        href={href}
        onClick={handleClick}
        disabled={isLoading}
        className={cn(
          "group inline-flex gap-2 items-center rounded-full leading-none duration-200 ease-in-out",
          {
            "text-sm px-6 py-4": size === "base",
            "text-sm px-4 py-2": size === "small",
          },
          {
            "bg-primary-500 text-primary-50 hover:bg-primary-600":
              color === "primary" && variant === "solid",
            "text-primary-500 bg-transparent px-0 py-1":
              color === "primary" && variant === "link",
            
            "bg-base-800 text-base-50 hover:bg-base-950 dark:invert":
              color === "dark",
            "bg-base-200 text-base-600 hover:bg-white dark:invert":
              color === "light",
            "bg-white text-base-600 hover:bg-base-200": color === "white",
            "bg-transparent text-base-600 ": color === "transparent",
            "opacity-70 cursor-not-allowed": isLoading,
          },
          { "hover:scale-95": variant !== "link" && !isLoading },
          { "w-full justify-center": block },
          className
        )}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {label && <span>Uploading...</span>}
          </>
        ) : (
          <>
            {leading && icon && <Icon icon={icon} className={iconClass} />}
            {label}
            {!leading && icon && <Icon icon={icon} className={iconClass} />}
          </>
        )}
      </Tag>
      
      {openFile && (
        <input
          type="file"
          ref={inputRef}
          style={{ display: "none" }}
          onChange={handleFileChange}
          accept="application/pdf" // ✅ Only allow PDF
          multiple={false} // ✅ Only one file
        />
      )}
    </>
  );
}